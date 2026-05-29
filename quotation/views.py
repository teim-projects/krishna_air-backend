from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, api_view
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
import logging
# from rest_framework.decorators import api_view, authentication_classes, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import (
    Quotation,
    QuotationVersion,
    QuotationHighSideItem,
    QuotationLowSideItem,
)
from .serializers import QuotationSerializer
from .utils.pdf_generator import generate_quotation_pdf

from .models import ServiceCategory, ServiceSubCategory, ServiceMaster, QuotationServiceItem
from .serializers import (
    ServiceCategorySerializer, 
    ServiceSubCategorySerializer,
    ServiceMasterSerializer, 
    QuotationServiceItemSerializer,
    QuotationServiceItemCreateSerializer
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
def thank_you_suggestions(request):
    search = request.GET.get('search', '')
    
    if len(search) < 2:
        return Response([])
    
    notes = Quotation.objects.filter(
        thank_you_note__icontains=search,
        thank_you_note__isnull=False
    ).exclude(thank_you_note='').values_list('thank_you_note', flat=True).distinct()[:10]
    
    return Response([{'id': i, 'text': note} for i, note in enumerate(notes)])

@api_view(['GET'])
def subject_suggestions(request):
    search = request.GET.get('search', '').strip()
    
    if not search or len(search) < 2:
        return Response([])
    
    quotations = Quotation.objects.filter(
        subject__icontains=search
    ).values('id', 'subject').distinct()[:10]
    
    return Response([{'id': q['id'], 'text': q['subject']} for q in quotations])


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
        try:
            quotation = self.get_object()

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
                return HttpResponse("No active version found", status=404)

            pdf_content = generate_quotation_pdf(quotation, version)

            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="quotation_{quotation.quotation_no}_v{version.version_no}.pdf"'

            return response

        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}")
            return HttpResponse(f"Error generating PDF: {str(e)}", status=500)
        
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
            response['Content-Disposition'] = f'inline; filename="quotation_{quotation.quotation_no}_v{version.version_no}.pdf"'
            
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


class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceCategory.objects.filter(is_active=True).prefetch_related(
        'subcategories__services__item',
        'services__item'
    )
    serializer_class = ServiceCategorySerializer
    pagination_class = None

class ServiceCategoryCreateViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    pagination_class = None

class ServiceSubCategoryCreateViewSet(viewsets.ModelViewSet):
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer
    pagination_class = None

class ServiceMasterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceMaster.objects.filter(is_active=True).select_related(
        'category', 'subcategory', 'item'
    )
    serializer_class = ServiceMasterSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'subcategory', 'service_type']

class QuotationServiceItemViewSet(viewsets.ModelViewSet):
    queryset = QuotationServiceItem.objects.all().select_related(
        'service__category', 'service__subcategory', 'service__item', 'quotation_version'
    )
    serializer_class = QuotationServiceItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['quotation_version']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return QuotationServiceItemCreateSerializer
        return QuotationServiceItemSerializer
    
    @action(detail=False, methods=['get'])
    def by_quotation_version(self, request):
        version_id = request.query_params.get('version_id')
        if not version_id:
            return Response({'error': 'version_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        items = self.queryset.filter(quotation_version_id=version_id)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
