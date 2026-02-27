# invoice/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, PublicInvoicePDFView


router = DefaultRouter()
router.register(r'invoice', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),  # This will handle all routes properly
    path('public-invoice/<int:pk>/pdf/', PublicInvoicePDFView.as_view(), name='public-invoice-pdf'),
]