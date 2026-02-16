from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework.response import Response
from rest_framework import status , filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from .models import Customer , lead_management , LeadFAQ ,LeadFollowUp
from .serializers import CustomerSerializer , LeadSerializer ,   LeadFollowUpSerializer, LeadFAQSerializer
from django.db.models import Q ,Case, When, Value, IntegerField
from django.utils import timezone
from .filters import LeadFilter
from rest_framework.decorators import action
from django.core.cache import cache

class CustomerViewsets(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('id')
    serializer_class = CustomerSerializer
    authentication_classes = [JWTAuthentication]   
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = [
        'name', '=email', 'secondary_email', 'contact_number',
        'poc_name', 'poc_contact_number', 'land_line_no',
        'city', 'state', 'site_city', 'site_state', 'pin_code'
    ]


class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = LeadFilter

    filterset_fields = ['assign_to', 'status','followup_date','date']
    search_fields = [
        'customer__id',
        'customer__name',
        'customer__contact_number',
        'customer__email',
        'project_name',
        'lead_source'
    ]

    def perform_create(self, serializer):
        user = self.request.user
        role_name = getattr(getattr(user, 'role', None), 'name', '').lower()

        # Always set created_by
        data = {
            "creatd_by": user,
            'date':timezone.localdate()
        }

        # If sales → auto assign to self
        if role_name == "sales":
            data["assign_to"] = user

        serializer.save(**data)

    def get_queryset(self):
        user = self.request.user
        today = timezone.localdate()

        queryset = (
            lead_management.objects
            .annotate(
                followup_priority=Case(
                    # 1️⃣ Today's followups
                    When(followup_date=today, then=Value(3)),

                    # 2️⃣ Future followups
                    When(followup_date__gt=today, then=Value(2)),

                    # 3️⃣ No followup
                    When(followup_date__isnull=True, then=Value(0)),

                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by(
                "-followup_priority",
                "-followup_date",
                "-date"
            )
        )

        # 🔹 SALES USER FILTER
        if getattr(user, 'role', None) and user.role.name.lower() == "sales":
            queryset = queryset.filter(assign_to=user)

        # 🔹 lead_source FILTER
        lead_source = self.request.query_params.get("lead_source")
        if lead_source:
            lead_source = lead_source.strip().lower()
            fixed_sources = self.get_serializer_class().FIXED_SOURCES

            if lead_source == "other":
                queryset = queryset.exclude(lead_source__in=fixed_sources)
            else:
                queryset = queryset.filter(lead_source=lead_source)

        return queryset
    
    @action(detail=False, methods=['get'], url_path='latest-lead-by-mobile')
    def latest_lead_by_mobile(self, request):
        mobile = request.query_params.get("mobile")

        if not mobile:
            return Response(
                {"error": "Mobile number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        lead = (
            lead_management.objects
            .select_related("customer")
            .filter(customer__contact_number=mobile)
            .order_by("-date", "-id")
            .first()
        )

        if not lead:
            return Response(
                {"message": "No lead found for this mobile number"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "project_name": lead.project_name,
            "address": lead.project_adderess if hasattr(lead.customer, "address") else None
        }, status=status.HTTP_200_OK)



class LeadFAQViewSet(viewsets.ModelViewSet):
    queryset = LeadFAQ.objects.all().order_by("sort_order", "id")
    serializer_class = LeadFAQSerializer
    permission_classes = [IsAuthenticated]


class LeadFollowUpViewSet(viewsets.ModelViewSet):
    """
    CRUD for follow-ups. Supports filtering by lead: ?lead=<lead_id>
    """
    serializer_class = LeadFollowUpSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            LeadFollowUp.objects
            .select_related("lead", "created_by")
            .prefetch_related("faq_answers__faq",
                              "lead__lead_products", )
        )
        lead_id = self.request.query_params.get("lead")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        return qs

    def perform_create(self, serializer):
        # created_by is set inside serializer.create but this is also ok
        serializer.save(created_by=self.request.user)

