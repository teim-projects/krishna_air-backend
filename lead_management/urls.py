
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewsets

router = DefaultRouter()
router.register(r'customer', CustomerViewsets, basename='customer')

urlpatterns = [
    
]

urlpatterns += router.urls