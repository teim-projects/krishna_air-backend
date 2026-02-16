from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuotationViewSet

router = DefaultRouter()

router.register(r'quotation',QuotationViewSet,basename='quotation')

urlpatterns = []

urlpatterns += router.urls
