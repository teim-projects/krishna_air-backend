from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework.response import Response
from rest_framework import status , filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from .models import Customer , lead_management , LeadFAQ ,LeadFollowUp
from .serializers import CustomerSerializer , LeadSerializer ,   LeadFollowUpSerializer, LeadFAQSerializer


class CustomerViewsets(viewsets.ModelViewSet):
  queryset = Customer.objects.all().order_by('id')
  serializer_class = CustomerSerializer
  authentication_classes = [JWTAuthentication]   
  permission_classes = [IsAuthenticated]
  filter_backends = [filters.SearchFilter]
  search_fields = ['name', '=email', 'contact_number','poc_name', 'poc_contact_number', 'land_line_no' ,'city','state' ,'site_city','site_state', 'pin_code']

# class LeadViewSet(viewsets.ModelViewSet):
#     queryset = lead_management.objects.all()
#     serializer_class = LeadSerializer
#     authentication_classes = [JWTAuthentication]  
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['assign_to','status','lead_source']
#     search_fields = ['customer__id','customer__name','customer__contact_number','customer__email',"project_name"]

#     def perform_create(self, serializer):
#         user = self.request.user
#         # defensive: ensure role exists, compare name case-insensitively
#         is_sales = False
#         if getattr(user, "role", None) and getattr(user.role, "name", None):
#             is_sales = user.role.name.strip().lower() == "sales"

#         if is_sales:
#             # Sales user -> assign lead to themselves regardless of payload
#             serializer.save(creatd_by=user, assign_to=user)
#         else:
#             # Non-sales -> set creatd_by and allow assign_to from payload (if provided)
#             assign_to = serializer.validated_data.get("assign_to", None)
#             serializer.save(creatd_by=user, assign_to=assign_to)


class LeadViewSet(viewsets.ModelViewSet):
    queryset = lead_management.objects.all()
    serializer_class = LeadSerializer
    authentication_classes = [JWTAuthentication] 
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['assign_to','status','lead_source']
    search_fields = ['customer__id','customer__name','customer__contact_number','customer__email',"project_name"]

  
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_authenticated and hasattr(user, 'role') and user.role:
            
            is_sales = False
            if getattr(user.role, "name", None):
                is_sales = user.role.name.strip().lower() == "sales"
            
            if is_sales:
                return queryset.filter(assign_to=user)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        is_sales = False
        if getattr(user, "role", None) and getattr(user.role, "name", None):
            is_sales = user.role.name.strip().lower() == "sales"

        if is_sales:
            serializer.save(creatd_by=user, assign_to=user) 
        else:
            assign_to = serializer.validated_data.get("assign_to", None)
            serializer.save(creatd_by=user, assign_to=assign_to)

class LeadFAQViewSet(viewsets.ModelViewSet):
    """
    CRUD for master FAQ questions.
    Frontend can call this to show list of standard questions.
    """
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
            .prefetch_related("faq_answers__faq")
        )
        lead_id = self.request.query_params.get("lead")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        return qs

    def perform_create(self, serializer):
        # created_by is set inside serializer.create but this is also ok
        serializer.save(created_by=self.request.user)