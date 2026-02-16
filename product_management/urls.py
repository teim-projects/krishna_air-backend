
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
# High side routes for AC products
router.register(r'actype', acTypeViewSet, basename='actype')
router.register(r'ac-subtypes', acSubTypesViewSet, basename='ac-subtypes')
router.register(r'ac-brand', brandViewSet, basename='brand')
router.register(r'product-model', productModelViewSet, basename='product-model')
router.register(r'product-variant', productVariabtViewSet, basename='product-variant')
router.register(r'product-inventory',productInventoryViewSet , basename='product-inventory')

# Low side routes for parts and accessories can be added here in the future as needed.
router.register(r'material-type', material_typeViewSet, basename='material-type')
router.register(r'item-type', item_typeViewSet, basename='item-type')
router.register(r'item-class', item_classViewSet, basename='item-class')
router.register(r'feature-type', feature_typeViewSet, basename='feature-type')
router.register(r'item', itemViewSet, basename='item')

urlpatterns = [
    
]

urlpatterns += router.urls