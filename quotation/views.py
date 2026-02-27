# quotation/views.py
from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
import logging

from .models import (
    Quotation,
    QuotationVersion,
    QuotationHighSideItem,
    QuotationLowSideItem,
)
from .serializers import QuotationSerializer
from .utils.pdf_generator import generate_quotation_pdf

logger = logging.getLogger(__name__)


class QuotationViewSet(viewsets.ModelViewSet):

    serializer_class = QuotationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter]

    search_fields = [
        "quotation_no",
        "customer__name",
        "customer__contact_number",
        "subject",
        "site_name",
    ]

    def get_queryset(self):
        """Simplified queryset - let the serializer handle nested relations"""
        try:
            # Just get quotations with customer, let serializer handle the rest
            return Quotation.objects.all().select_related("customer").order_by("-id")
        except Exception as e:
            logger.error(f"Error in get_queryset: {str(e)}")
            return Quotation.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["get"], url_path="latest-version")
    def latest_version(self, request, pk=None):
        quotation = self.get_object()
        version = quotation.versions.filter(is_active=True).first()

        if not version:
            return Response(
                {"message": "No active version found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(quotation)
        return Response(serializer.data)

    # PDF ACTIONS
    # quotation/views.py

    @action(detail=True, methods=['get'], url_path='pdf')
    def download_pdf(self, request, pk=None):
        """Generate PDF for active version"""
        try:
            quotation = self.get_object()
            # Get the version with all related data using correct paths
            version = QuotationVersion.objects.filter(
                quotation=quotation, 
                is_active=True
            ).prefetch_related(
                'high_side_items__product_variant__product_model',
                'high_side_items__product_variant',
                'low_side_items__item',
                'low_side_items__item__material_type_id',
                'low_side_items__item__item_type_id',
                'low_side_items__item__feature_type_id',
                'low_side_items__item__brand'
            ).first()
            
            if not version:
                return HttpResponse(
                    "No active version found for this quotation",
                    status=404
                )
            
            pdf_content = generate_quotation_pdf(quotation, version)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="quotation_{quotation.quotation_no}_v{version.version_no}.pdf"'
            
            return response
        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}")
            return HttpResponse(
                f"Error generating PDF: {str(e)}",
                status=500
            )
    
    @action(detail=True, methods=['get'], url_path='version/(?P<version_id>[^/.]+)/pdf')
    def download_version_pdf(self, request, pk=None, version_id=None):
        """Generate PDF for specific version"""
        try:
            quotation = self.get_object()
            version = get_object_or_404(
                QuotationVersion.objects.prefetch_related(
                    'high_side_items__product_variant__product_model',
                    'high_side_items__product_variant',
                    'low_side_items__item',
                    'low_side_items__item__material_type_id',
                    'low_side_items__item__item_type_id',
                    'low_side_items__item__feature_type_id',
                    'low_side_items__item__brand'
                ), 
                pk=version_id, 
                quotation=quotation
            )
            
            pdf_content = generate_quotation_pdf(quotation, version)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="quotation_{quotation.quotation_no}_v{version.version_no}.pdf"'
            
            return response
        except Exception as e:
            logger.error(f"Version PDF generation error: {str(e)}")
            return HttpResponse(
                f"Error generating PDF: {str(e)}",
                status=500
            )


    @action(detail=True, methods=["delete"], url_path="version/(?P<version_id>[^/.]+)/delete")
    def delete_version(self, request, pk=None, version_id=None):
    
        quotation = self.get_object()
    
        version = get_object_or_404(
            QuotationVersion,
            pk=version_id,
            quotation=quotation
        )
    
        was_active = version.is_active
        version.delete()
    
        # remaining versions
        remaining_versions = quotation.versions.order_by("-created_at")
    
        # if no versions left → delete quotation
        if not remaining_versions.exists():
            quotation.delete()
            return Response({"message": "Quotation deleted (last version removed)"})
    
        # if active version deleted → activate latest remaining
        if was_active:
            latest = remaining_versions.first()
            latest.is_active = True
            latest.save(update_fields=["is_active"])
    
        return Response({"message": "Version deleted"})
