from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework import status , filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import acTypeSerializer , acSubTypesSerializer, brandSerializer


class acTypeViewSet(ModelViewSet):
    queryset = acType.objects.all()
    serializer_class = acTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']



class acSubTypesViewSet(ModelViewSet):
    queryset = acSubTypes.objects.all()
    serializer_class = acSubTypesSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']



class brandViewSet(ModelViewSet):
    queryset = brand.objects.all()
    serializer_class = brandSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']
