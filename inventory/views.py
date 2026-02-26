from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import *
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response


class VendorViewSet(ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active', 'state', 'supplier_category', 'company_type']
    search_fields = ['name', 'email', 'mobile', 'gst_details', 'pan_details', 'office_poc_name']




# --------------------------------------------------------------------------------
# Terms Condition Viewsets
# --------------------------------------------------------------------------------

class TermsConditionTypeViewsets(ModelViewSet):
    queryset = TermsConditionType.objects.all()
    serializer_class = TermsConditionTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name"]
    # search_fields = ['name']


class TermsConditionViewsets(ModelViewSet):
    queryset = TermsConditions.objects.all()
    serializer_class = TermsConditionsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend,  filters.SearchFilter]
    filterset_fields = ["terms_condition_type","terms"]
    search_fields = ['terms', 'terms_condition_type__name']



class PurchaseOrderViewSet(ModelViewSet):
    queryset = PurchaseOrder.objects.filter(is_current=True).prefetch_related("products")
    serializer_class = PurchaseOrderSerializer
    
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend,  filters.SearchFilter]
    filterset_fields = ["branch",]
    search_fields = ['vendor', 'site',"purchase_order_no","quotation_ref_no","contact_name","contact_no"]

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        po = self.get_object()  # this will always be current version here

        po_no = po.purchase_order_no

        # 🧨 Delete ALL versions for this PO number
        PurchaseOrder.objects.filter(purchase_order_no=po_no).delete()

        return Response(
            {"detail": f"All versions of PO {po_no} deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


class PurchaseOrderHistoryViewSet(ReadOnlyModelViewSet):
    serializer_class = PurchaseOrderSerializer
    http_method_names = ["get", "delete"] 

    def get_queryset(self):
        po_no = self.request.query_params.get("purchase_order_no")

        qs = PurchaseOrder.objects.all().order_by("-version")

        if po_no:
            qs = qs.filter(purchase_order_no=po_no)

        return qs
    
    def destroy(self, request, *args, **kwargs):
        po = self.get_object()

        # ❌ Prevent deleting current from history endpoint (optional safety)
        if po.is_current:
            return Response(
                {"detail": "Delete current PO from main endpoint only."},
                status=status.HTTP_400_BAD_REQUEST
            )

        po.delete()
        return Response(
            {"detail": f"PO version v{po.version} deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )