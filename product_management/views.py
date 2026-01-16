from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework import status , filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import acTypeSerializer , acSubTypesSerializer, brandSerializer , productModelSerializer , productVariantSerializer, productInventorySerializer


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


class productModelViewSet(ModelViewSet):
    queryset = ProductModel.objects.all()
    serializer_class = productModelSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['brand_id','ac_sub_type_id','is_active','inverter','phase']
    search_fields  = ['name','model_no']

class productVariabtViewSet(ModelViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = productVariantSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active','product_model__inverter','product_model__phase']
    search_fields  = ['sku','capacity']


class productInventoryViewSet(ModelViewSet):
    queryset = ProductInventory.objects.all()
    serializer_class = productInventorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 
                        'purchase_date',
                        'product_variant__product_model__brand_id__name'
                        ]
    
    search_fields  = ['serial_no',
                      'product_variant__sku',
                      'product_variant__capacity'
                      ]

