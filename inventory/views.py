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
from rest_framework.decorators import action

class VendorViewSet(ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active', 'state', 'supplier_category', 'company_type']
    search_fields = ['name', 'email', 'mobile', 'gst_details', 'pan_details', 'office_poc_name']
    pagination_class = None  # Disable pagination to show all vendors in dropdown




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

    def create(self, request, *args, **kwargs):

        # If terms is list → bulk create
        if isinstance(request.data.get("terms"), list):
            serializer = TermsConditionsBulkSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            objects = serializer.save()

            return Response(
                TermsConditionsSerializer(objects, many=True).data,
                status=status.HTTP_201_CREATED
            )

        # Else normal single create
        return super().create(request, *args, **kwargs)

class PurchaseOrderViewSet(ModelViewSet):
    queryset = PurchaseOrder.objects.filter(is_current=True).prefetch_related("products")
    serializer_class = PurchaseOrderSerializer
    
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend,  filters.SearchFilter]
    filterset_fields = ["branch",]
    search_fields = ['vendor__name', 'site__name',"purchase_order_no","quotation_ref_no","contact_name","contact_no"]

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
            qs = qs.filter(purchase_order_no=po_no , is_current =  False)

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
    
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from weasyprint import HTML
from decimal import Decimal
from .models import PurchaseOrder
from .utils import format_amount_in_words


def purchase_order_pdf(request, pk):

    po = PurchaseOrder.objects.get(pk=pk)
    products = list(po.products.select_related(
        "item__material_type_id",
        "item__item_type_id",
        "item__feature_type_id",
        "item__item_class_id",
        "product_variant__product_model"
    ).all())

    # Dynamically renumber products for rendering/PDF display
    section_counter = 0
    child_counter = 0
    for p in products:
        if p.is_section:
            section_counter += 1
            child_counter = 0
            p.serial_no = str(section_counter)
        else:
            if section_counter > 0:
                child_counter += 1
                p.serial_no = f"{section_counter}.{child_counter}"
            else:
                child_counter += 1
                p.serial_no = str(child_counter)

    gst_amount = (po.subtotal * po.gst_percentage) / Decimal("100")

    # Convert total amount to words
    total_in_words = format_amount_in_words(po.grand_total)

    # logo_path = finders.find("images/ka-logo.png")

    html_string = render_to_string(
        "pdf/purchase_order.html",
        {
            "po": po,
            "products": products,
            "gst_amount": gst_amount,
            "total_in_words": total_in_words,  # Add total in words
            # "logo_path": logo_path,
        }
    )

    # print("LOGO PATH:", logo_path)

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    if request.GET.get("download"):
        response["Content-Disposition"] = f'attachment; filename="PO-{po.purchase_order_no}.pdf"'
    else:
        response["Content-Disposition"] = f'inline; filename="PO-{po.purchase_order_no}.pdf"'

    return response




class GRNViewSet(ModelViewSet):
    queryset = GRN.objects.all().select_related(
        "purchase_order__vendor"
    ).order_by("-id")
    serializer_class = GRNSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # ── search & ordering ────────────────────────────────────────────────────────
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "grn_no",
        "purchase_order__purchase_order_no",   # search by PO number
        "purchase_order__vendor__name",         # search by vendor name
    ]
    ordering_fields = ["grn_date", "id"]
    ordering = ["-id"]

    def create(self, request, *args, **kwargs):
        """
        Create GRN with better error handling
        """
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """
        Prevent editing completed GRNs
        """
        grn = self.get_object()
        
        if grn.is_completed:
            return Response(
                {"error": "Cannot edit completed GRN. Inventory already updated."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Prevent deleting completed GRNs
        """
        grn = self.get_object()
        
        if grn.is_completed:
            return Response(
                {"error": "Cannot delete completed GRN. Inventory already updated."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """
        Manual complete endpoint (optional - GRN auto-completes on create)
        Kept for backward compatibility or manual completion if needed
        """
        grn = self.get_object()

        if grn.is_completed:
            return Response(
                {"error": "GRN already completed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Complete the GRN
        with transaction.atomic():
            grn.is_completed = True
            grn.save(update_fields=["is_completed"])
            complete_grn(grn)

        return Response({"message": "GRN completed successfully"})
    
    

class InventoryViewSet(ModelViewSet):
    queryset = InventoryItem.objects.all().order_by("-updated_at")
    serializer_class = InventorySerializer
    # permission_classes = [IsAuthenticated]

    # 🔍 filtering & search
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["product_variant", "item"]
    search_fields = [
        "product_variant__name",
        "item__name"
    ]

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Return all inventory items without pagination (for dropdown selects)"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def low_side(self, request):
        """Return only low-side material items (exclude high-side ACs) without pagination"""
        queryset = self.get_queryset().filter(
            item__isnull=False,
            product_variant__isnull=True
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class MaterialIssueViewSet(ModelViewSet):
    queryset = MaterialIssue.objects.all().prefetch_related(
        "items__inventory_item__product_variant__product_model__brand_id",
        "items__inventory_item__item__material_type_id",
        "items__inventory_item__item__item_type_id",
    )
    serializer_class = MaterialIssueSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        issue = serializer.save()

        return Response(
            self.get_serializer(issue).data,
            status=status.HTTP_201_CREATED
        )
        

class MaterialReturnViewSet(ModelViewSet):
    queryset = MaterialReturn.objects.all().prefetch_related("items")
    serializer_class = MaterialReturnSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # ✅ Create Return
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        material_return = serializer.save(created_by=request.user)

        return Response(
            self.get_serializer(material_return).data,
            status=status.HTTP_201_CREATED
        )

    # ✅ Complete Return (VERY IMPORTANT)
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        material_return = self.get_object()

        # 🔥 Prevent duplicate completion
        if getattr(material_return, "is_completed", False):
            return Response(
                {"error": "Return already completed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not material_return.items.exists():
            return Response(
                {"error": "No return items found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # 🔥 CALL YOUR FUNCTION
            complete_return(material_return)

            # ✅ mark completed (if field exists)
            if hasattr(material_return, "is_completed"):
                material_return.is_completed = True
                material_return.save(update_fields=["is_completed"])

        return Response({"message": "Return completed successfully"})

    # ✅ Filter by issue (optional but useful)
    def get_queryset(self):
        queryset = super().get_queryset()

        issue_id = self.request.query_params.get("material_issue")

        if issue_id:
            queryset = queryset.filter(material_issue_id=issue_id)

        return queryset.order_by("-id")
    
    
class DeliveryChallanViewSet(ModelViewSet):

    queryset = DeliveryChallan.objects.all().select_related(
        "material_issue", "branch", "site"
    ).prefetch_related(
        "items__material_issue_item__inventory_item"
    )

    serializer_class = DeliveryChallanSerializer

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        "status",
        "material_issue"
    ]

    search_fields = [
        "dc_number",
        "material_issue__issue_number",
        "delivery_partner_name",
        "delivery_person_name",
        "delivery_person_phone",
        "branch__name",
        "site__name",
    ]

    @action(detail=True, methods=["post"])
    def mark_in_transit(self, request, pk=None):

        dc = self.get_object()

        dc.status = "in_transit"
        dc.save(update_fields=["status"])

        return Response(
            {"message": "Marked In Transit"}
        )

    @action(detail=True, methods=["post"])
    def mark_delivered(self, request, pk=None):

        dc = self.get_object()

        dc.status = "delivered"
        dc.delivery_date = request.data.get(
            "delivery_date"
        )

        dc.receiver_name = request.data.get(
            "receiver_name"
        )

        dc.receiver_mobile = request.data.get(
            "receiver_mobile"
        )

        if request.FILES.get("delivery_proof"):
            dc.delivery_proof = request.FILES.get(
                "delivery_proof"
            )

        dc.save()

        return Response(
            {"message": "Delivery Completed"}
        )

from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

from .models import DeliveryChallan, PurchaseOrderProduct


def delivery_challan_pdf(request, pk):

    dc = DeliveryChallan.objects.select_related(
        "material_issue",
        "material_issue__site",
        "material_issue__branch",
        "branch",
        "site",
    ).prefetch_related(
        "items__material_issue_item__inventory_item__product_variant__product_model__brand_id",
        "items__material_issue_item__inventory_item__product_variant__product_model__ac_sub_type_id__ac_type_id",
        "items__material_issue_item__inventory_item__item__material_type_id",
        "items__material_issue_item__inventory_item__item__item_type_id",
    ).get(pk=pk)

    items = dc.items.all()

    grand_total = 0
    contact_person = dc.delivery_person_name or ""
    contact_no = dc.delivery_person_phone or ""

    if dc.destination_type == "branch" and dc.branch_id:
        destination_name = dc.branch.name
    elif dc.destination_type == "site" and dc.site_id:
        destination_name = dc.site.name
    elif dc.material_issue and dc.material_issue.site_id:
        destination_name = dc.material_issue.site.name
    else:
        destination_name = ""

    for dc_item in items:
        inventory_item = dc_item.material_issue_item.inventory_item

        # Same display name as DC form / Material Issue view
        dc_item.product_name = get_inventory_item_display_name(inventory_item)
        dc_item.uom = (
            dc_item.material_issue_item.uom
            or (inventory_item.uom if inventory_item else None)
            or "Nos"
        )

        # Rate: latest PO rate, else variant DP/MRP (same helper as form)
        rate = get_inventory_item_rate(inventory_item)
        dc_item.rate = rate or 0
        dc_item.amount = (dc_item.quantity or 0) * (dc_item.rate or 0)

        # Fallback contact from PO if delivery person not set
        if not contact_person or not contact_no:
            po_product = None
            if inventory_item and inventory_item.product_variant_id:
                po_product = PurchaseOrderProduct.objects.filter(
                    product_variant=inventory_item.product_variant,
                    is_section=False,
                ).order_by("-id").first()
            elif inventory_item and inventory_item.item_id:
                po_product = PurchaseOrderProduct.objects.filter(
                    item=inventory_item.item,
                    is_section=False,
                ).order_by("-id").first()

            if po_product and po_product.purchase_order:
                if not contact_person:
                    contact_person = po_product.purchase_order.contact_name or ""
                if not contact_no:
                    contact_no = po_product.purchase_order.contact_no or ""

        grand_total += dc_item.amount

    html_string = render_to_string(
        "pdf/delivery_challan.html",
        {
            "dc": dc,
            "items": items,
            "grand_total": grand_total,
            "contact_person": contact_person,
            "contact_no": contact_no,
            "destination_name": destination_name,
            "delivery_partner_name": dc.delivery_partner_name or "",
        }
    )

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf()

    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )

    if request.GET.get("download"):
        response["Content-Disposition"] = (
            f'attachment; filename="DC-{dc.dc_number}.pdf"'
        )
    else:
        response["Content-Disposition"] = (
            f'inline; filename="DC-{dc.dc_number}.pdf"'
        )

    return response