from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.db.models import Prefetch

from .models import Invoice, InvoiceItem, InvoiceTaxBreakup
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
            .select_related("customer")
            .prefetch_related(
                "items",
                "tax_breakups"
            )
            .order_by("-id")
        )
    

    # In views.py - update the download_pdf method
    @action(detail=True, methods=['get'], url_path='pdf')
    def download_pdf(self, request, pk=None):
        """Generate and download PDF for invoice"""
        # Check for token in query params if needed
        token = request.query_params.get('token')
        if token:
            # Validate token here if needed
            pass
        
        invoice = self.get_object()
        pdf_content = generate_invoice_pdf(invoice)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_no}.pdf"'
        
        return response


     # views.py - Add this new view

# Keep your existing InvoiceViewSet as is (remove the token query param code)

class PublicInvoicePDFView(APIView):
    """
    Public endpoint to view invoice PDFs with token validation
    """
    authentication_classes = []  # No authentication
    permission_classes = []  # No permission classes
    
    def get(self, request, pk):
        # Get token from query params
        token = request.query_params.get('token')
        
        if not token:
            return HttpResponse(
                "Authentication token required", 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Validate the token
        try:
            # Decode and validate the token
            jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredTokenError:
            return HttpResponse(
                "Token has expired", 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except jwt.InvalidTokenError:
            return HttpResponse(
                "Invalid token", 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get the invoice
        invoice = get_object_or_404(Invoice, pk=pk)
        
        # Generate PDF
        pdf_content = generate_invoice_pdf(invoice)
        
        # Create response
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="invoice_{invoice.invoice_no}.pdf"'
        
        return response
