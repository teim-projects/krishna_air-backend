from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    QuotationViewSet, 
    thank_you_suggestions, 
    subject_suggestions, 
    ServiceCategoryViewSet, 
    ServiceCategoryCreateViewSet,
    ServiceSubCategoryCreateViewSet,
    ServiceMasterViewSet,
    ServiceMasterCreateViewSet, 
    QuotationServiceItemViewSet
)

router = DefaultRouter()

router.register(r'quotation',QuotationViewSet,basename='quotation')
router.register(r'service-categories', ServiceCategoryViewSet)
router.register(r'service-masters', ServiceMasterViewSet)
router.register(r'service-masters-create', ServiceMasterCreateViewSet, basename='service-masters-create')
router.register(r'quotation-service-items', QuotationServiceItemViewSet)
router.register(r'service-categories-create', ServiceCategoryCreateViewSet, basename='service-categories-create')
router.register(r'service-subcategories', ServiceSubCategoryCreateViewSet, basename='service-subcategories')


urlpatterns = [
    path('thank-you-suggestions/', thank_you_suggestions, name='thank_you_suggestions'),
    path('subject-suggestions/', subject_suggestions, name='subject_suggestions'),
]

urlpatterns += router.urls
