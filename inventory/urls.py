from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r"terms-type",TermsConditionTypeViewsets, basename='terms-type')
router.register(r'terms',TermsConditionViewsets,basename='terms')
router.register(r"purchase-orders", PurchaseOrderViewSet, basename="po")
router.register(r"purchase-orders-history", PurchaseOrderHistoryViewSet, basename="po-history")


urlpatterns = router.urls
