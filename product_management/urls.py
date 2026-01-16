
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import acTypeViewSet , acSubTypesViewSet, brandViewSet , productModelViewSet , productVariabtViewSet, productInventoryViewSet

router = DefaultRouter()
router.register(r'actype', acTypeViewSet, basename='actype')
router.register(r'ac-subtypes', acSubTypesViewSet, basename='ac-subtypes')
router.register(r'ac-brand', brandViewSet, basename='brand')
router.register(r'product-model', productModelViewSet, basename='product-model')
router.register(r'product-variant', productVariabtViewSet, basename='product-variant')
router.register(r'product-inventory',productInventoryViewSet , basename='product-inventory')

urlpatterns = [
    
]

urlpatterns += router.urls