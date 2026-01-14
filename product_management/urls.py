
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import acTypeViewSet

router = DefaultRouter()
router.register(r'actype', acTypeViewSet, basename='actype')

urlpatterns = [
    
]

urlpatterns += router.urls