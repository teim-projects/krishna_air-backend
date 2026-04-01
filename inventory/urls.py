from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from inventory import views

router = DefaultRouter()
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r"terms-type",TermsConditionTypeViewsets, basename='terms-type')
router.register(r'terms',TermsConditionViewsets,basename='terms')
router.register(r"purchase-orders", PurchaseOrderViewSet, basename="po")
router.register(r"purchase-orders-history", PurchaseOrderHistoryViewSet, basename="po-history")
router.register(r"grn", GRNViewSet, basename="grn")
router.register(r"inventory", InventoryViewSet, basename="inventory")
router.register(r"material-issue", MaterialIssueViewSet, basename="material-issue")


urlpatterns = [
    path("", include(router.urls)),
    path(
        "purchase-order/<int:pk>/pdf/",
        views.purchase_order_pdf,
        name="purchase_order_pdf"
)
]
