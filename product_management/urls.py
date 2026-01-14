
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import acTypeViewSet , acSubTypesViewSet, brandViewSet

router = DefaultRouter()
router.register(r'actype', acTypeViewSet, basename='actype')
router.register(r'ac-subtypes', acTypeViewSet, basename='ac-subtypes')
router.register(r'ac-brand', acTypeViewSet, basename='brand')

urlpatterns = [
    
]

urlpatterns += router.urls