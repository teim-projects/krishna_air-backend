from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AMCPackageViewSet, AMCContractViewSet, AMCServiceViewSet,
    AMCInvoiceViewSet, AMCRenewalViewSet
)

router = DefaultRouter()
router.register(r'packages', AMCPackageViewSet, basename='amc-package')
router.register(r'contracts', AMCContractViewSet, basename='amc-contract')
router.register(r'services', AMCServiceViewSet, basename='amc-service')
router.register(r'invoices', AMCInvoiceViewSet, basename='amc-invoice')
router.register(r'renewals', AMCRenewalViewSet, basename='amc-renewal')

urlpatterns = [
    path('', include(router.urls)),
]
