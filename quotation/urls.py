from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    QuotationViewSet, 
    thank_you_suggestions, 
    subject_suggestions,
    ServiceMasterViewSet,
    ServiceMasterCreateViewSet, 
    QuotationServiceItemViewSet,
    QuotationCustomerViewSet,
    generate_quotation_pdf
)

router = DefaultRouter()

router.register(r'quotation', QuotationViewSet, basename='quotation')
router.register(r'service-masters', ServiceMasterViewSet, basename='service-masters')
router.register(r'service-masters-create', ServiceMasterCreateViewSet, basename='service-masters-create')
router.register(r'quotation-service-items', QuotationServiceItemViewSet, basename='quotation-service-items')
router.register(r'customer', QuotationCustomerViewSet, basename='quotation-customer')

urlpatterns = [
    path('thank-you-suggestions/', thank_you_suggestions, name='thank_you_suggestions'),
    path('subject-suggestions/', subject_suggestions, name='subject_suggestions'),
    path('quotations/<int:quotation_id>/pdf/', generate_quotation_pdf, name='quotation-pdf'),
]

urlpatterns += router.urls
