from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework.response import Response
from rest_framework import status , filters
from rest_framework import viewsets
from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewsets(viewsets.ModelViewSet):
  queryset = Customer.objects.all().order_by('id')
  serializer_class = CustomerSerializer
  authentication_classes = [JWTAuthentication]   
  permission_classes = [IsAuthenticated]
  filter_backends = [filters.SearchFilter]
  search_fields = ['^name', '=email', 'contact_number', 'city','state' ,'site_city','site_state']

  