from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuotationViewSet, thank_you_suggestions, subject_suggestions

router = DefaultRouter()

router.register(r'quotation',QuotationViewSet,basename='quotation')

urlpatterns = [
    path('thank-you-suggestions/', thank_you_suggestions, name='thank_you_suggestions'),
    path('subject-suggestions/', subject_suggestions, name='subject_suggestions'),
]

urlpatterns += router.urls
