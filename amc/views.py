from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import (
    AMCPackage, AMCContract, AMCService, 
    AMCServiceParts, AMCServiceLabor, AMCInvoice, AMCRenewal
)
from .serializers import (
    AMCPackageSerializer, AMCContractSerializer, AMCServiceSerializer,
    AMCServicePartsSerializer, AMCServiceLaborSerializer, AMCInvoiceSerializer,
    AMCRenewalSerializer
)


class AMCPackageViewSet(viewsets.ModelViewSet):
    queryset = AMCPackage.objects.filter(is_active=True)
    serializer_class = AMCPackageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get packages by type (COMPREHENSIVE or NON_COMPREHENSIVE)"""
        package_type = request.query_params.get('type')
        if not package_type:
            return Response({'error': 'type parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        packages = self.queryset.filter(package_type=package_type)
        serializer = self.get_serializer(packages, many=True)
        return Response(serializer.data)


class AMCContractViewSet(viewsets.ModelViewSet):
    queryset = AMCContract.objects.all()
    serializer_class = AMCContractSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer', 'status', 'amc_included_in_sale']
    search_fields = ['contract_number', 'customer__name']
    
    @action(detail=False, methods=['get'])
    def active_contracts(self, request):
        """Get all active AMC contracts"""
        contracts = self.queryset.filter(status='ACTIVE')
        serializer = self.get_serializer(contracts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get contracts expiring in next 30 days"""
        today = timezone.now().date()
        expiry_date = today + timedelta(days=30)
        
        contracts = self.queryset.filter(
            amc_end_date__lte=expiry_date,
            amc_end_date__gte=today,
            status='ACTIVE'
        )
        serializer = self.get_serializer(contracts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_renewal(self, request, pk=None):
        """Create renewal for expiring contract"""
        contract = self.get_object()
        
        # Check if already renewed
        if AMCRenewal.objects.filter(previous_contract=contract, status='RENEWED').exists():
            return Response(
                {'error': 'Contract already renewed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new renewal contract
        new_contract = AMCContract.objects.create(
            customer=contract.customer,
            package=contract.package,
            product_variant=contract.product_variant,
            sale_date=contract.sale_date,
            warranty_end_date=contract.warranty_end_date,
            amc_start_date=contract.amc_end_date + timedelta(days=1),
            amc_end_date=contract.amc_end_date + timedelta(days=365),
            amc_included_in_sale=False,
            status='ACTIVE',
            amc_cost=request.data.get('amc_cost', contract.amc_cost),
            is_renewal=True,
            previous_contract=contract
        )
        
        # Track renewal
        AMCRenewal.objects.create(
            previous_contract=contract,
            new_contract=new_contract,
            renewal_date=timezone.now().date(),
            renewal_cost=new_contract.amc_cost,
            status='RENEWED'
        )
        
        serializer = self.get_serializer(new_contract)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AMCServiceViewSet(viewsets.ModelViewSet):
    queryset = AMCService.objects.all()
    serializer_class = AMCServiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['amc_contract', 'service_type', 'status']
    
    def perform_create(self, serializer):
        instance = serializer.save()
        
        # If non-comprehensive and service is completed, create invoice
        if instance.amc_contract.package.package_type == 'NON_COMPREHENSIVE':
            if instance.status == 'COMPLETED':
                self._create_invoice_for_service(instance)
    
    def _create_invoice_for_service(self, service):
        """Auto-create invoice for non-comprehensive services"""
        parts_total = sum([p.total_cost for p in service.parts_used.filter(include_in_customer_invoice=True)])
        labor_total = service.labor.total_labor_cost if hasattr(service, 'labor') and service.labor.include_in_customer_invoice else 0
        
        if parts_total > 0 or labor_total > 0:
            AMCInvoice.objects.create(
                service=service,
                parts_total=parts_total,
                labor_total=labor_total,
                other_charges=0
            )
    
    @action(detail=True, methods=['post'])
    def add_parts(self, request, pk=None):
        """Add parts used in service"""
        service = self.get_object()
        
        inventory_item_id = request.data.get('inventory_item')
        quantity = request.data.get('quantity', 1)
        rate = request.data.get('rate_per_unit')
        include_in_invoice = request.data.get('include_in_customer_invoice', False)
        
        part = AMCServiceParts.objects.create(
            service=service,
            inventory_item_id=inventory_item_id,
            quantity_used=quantity,
            rate_per_unit=rate,
            include_in_customer_invoice=include_in_invoice
        )
        
        serializer = AMCServicePartsSerializer(part)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AMCInvoiceViewSet(viewsets.ModelViewSet):
    queryset = AMCInvoice.objects.all()
    serializer_class = AMCInvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['payment_status']
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark invoice as paid"""
        invoice = self.get_object()
        invoice.payment_status = 'PAID'
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class AMCRenewalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AMCRenewal.objects.all()
    serializer_class = AMCRenewalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
