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
  search_fields = ['^name', '=email', 'contact_number', 'city','state' ,'site_city','site_state']

class LeadViewSet(viewsets.ModelViewSet):
    queryset = lead_management.objects.all()
    serializer_class = LeadSerializer
    # authentication_classes = [JWTAuthentication]  
    permission_classes = []


class LeadFAQViewSet(viewsets.ModelViewSet):
    """
    CRUD for master FAQ questions.
    Frontend can call this to show list of standard questions.
    """
    queryset = LeadFAQ.objects.all().order_by("sort_order", "id")
    serializer_class = LeadFAQSerializer
    # permission_classes = [IsAuthenticated]


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