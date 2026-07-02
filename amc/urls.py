from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AMCContractViewSet,
    AMCRenewalViewSet,
    ServiceManagementRecordViewSet,
    ServiceManagementMaterialViewSet,
    CustomerViewSet
)

router = DefaultRouter()
router.register(r'contracts', AMCContractViewSet, basename='amc-contract')
router.register(r'renewals', AMCRenewalViewSet, basename='amc-renewal')
router.register(r'service-records', ServiceManagementRecordViewSet, basename='service-record')
router.register(r'service-materials', ServiceManagementMaterialViewSet, basename='service-material')
router.register(r'customers', CustomerViewSet, basename='customer')


urlpatterns = [
    path('', include(router.urls)),
    path('lead-management/', include('lead_management.urls')),
    path('quotation/', include('quotation.urls')),
]
