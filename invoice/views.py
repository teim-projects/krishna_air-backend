from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.db.models import Prefetch

import invoice

from .models import Invoice  
from .serializers import InvoiceSerializer
from django.http import HttpResponse
from rest_framework.decorators import action
from .utils.pdf_generator import generate_invoice_pdf
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
import jwt
from django.conf import settings



class InvoiceViewSet(viewsets.ModelViewSet):

    serializer_class = InvoiceSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter]

    search_fields = [
        "invoice_no",
        "buyer_name",
        "site_name",
    ]

    def get_queryset(self):

        return (
            Invoice.objects
            .select_related("customer","branch","site")
            .prefetch_related(
                "terms_conditions",
                "high_side_items__product_variant__product_model__brand_id",
                "high_side_items__product_variant__product_model__ac_sub_type_id__ac_type_id",
                "low_side_items__item__material_type_id",
                "low_side_items__item__item_type_id",
                "low_side_items__item__feature_type_id",
                "low_side_items__item__item_class_id",
                
            )
            .order_by("-id")
        )
    

    # In views.py - update the download_pdf method
    # @action(detail=True, methods=['get'], url_path='pdf')
    # def download_pdf(self, request, pk=None):
    #     """Generate and download PDF for invoice"""
    #     # Check for token in query params if needed
    #     token = request.query_params.get('token')
    #     if token:
    #         # Validate token here if needed
    #         pass
        
    #     invoice = self.get_object()
    #     pdf_content = generate_invoice_pdf(invoice)
        
    #     response = HttpResponse(pdf_content, content_type='application/pdf')
    #     response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_no}.pdf"'
        
    #     return response


    #  # views.py - Add this new view


# Keep your existing InvoiceViewSet as is (remove the token query param code)

# class PublicInvoicePDFView(APIView):
#     """
#     Public endpoint to view invoice PDFs with token validation
#     """
#     authentication_classes = []  # No authentication
#     permission_classes = []  # No permission classes
    
#     def get(self, request, pk):
#         # Get token from query params
#         token = request.query_params.get('token')
        
#         if not token:
#             return HttpResponse(
#                 "Authentication token required", 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         # Validate the token
#         try:
#             # Decode and validate the token
#             jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
#         except jwt.ExpiredTokenError:
#             return HttpResponse(
#                 "Token has expired", 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
#         except jwt.InvalidTokenError:
#             return HttpResponse(
#                 "Invalid token", 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         # Get the invoice
#         invoice = get_object_or_404(Invoice, pk=pk)
        
#         # Generate PDF
#         pdf_content = generate_invoice_pdf(invoice)
        
#         # Create response
#         response = HttpResponse(pdf_content, content_type='application/pdf')
#         response['Content-Disposition'] = f'inline; filename="invoice_{invoice.invoice_no}.pdf"'
        
#         return response


from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal
from .models import Invoice
from num2words import num2words

def invoice_pdf(request, pk):

    invoice = Invoice.objects.get(pk=pk)

    high_items = list(invoice.high_side_items.all())
    low_items = list(invoice.low_side_items.all())

    products = high_items + low_items

    total_qty = sum(p.quantity for p in products)
    invoice_payment_terms = invoice.terms_conditions.filter(
    terms_condition_type__name="Invoice Payment"
        )
    
    invoice_delivery_terms = invoice.terms_conditions.filter(
    terms_condition_type__name="Invoice Delivery"
        )
    
    # Initialize
    cgst = None
    sgst = None
    igst = None

    if invoice.gst_type == "CGST_SGST":
        cgst = invoice.gst_percentage / Decimal(2)
        sgst = invoice.gst_percentage / Decimal(2)

    else:
        igst = invoice.gst_percentage


    total_tax_in_words = num2words(invoice.total_tax, lang='en').capitalize() + " Rupees Only"
    html_string = render_to_string(
        "pdf/invoice.html",
        {
            "invoice": invoice,
            "products": products,
            "total_qty": total_qty,
            "total_tax_in_words": total_tax_in_words,
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,   
            "invoice_payment_terms": invoice_payment_terms,
            "invoice_delivery_terms": invoice_delivery_terms,

        }
    )

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")

    if request.GET.get("download"):
        response["Content-Disposition"] = f'attachment; filename="INV-{invoice.invoice_no}.pdf"'
    else:
        response["Content-Disposition"] = f'inline; filename="INV-{invoice.invoice_no}.pdf"'

    return response