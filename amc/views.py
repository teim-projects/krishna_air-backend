from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch, Q
from rest_framework import filters
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Customer
from .serializers import CustomerSearchSerializer


from .models import AMCContract, AMCRenewal, AMCSparePart, TechnicianWorkRecord

from .serializers import (
    AMCContractSerializer,
    AMCRenewalSerializer,
    AMCSparePartSerializer,
    TechnicianWorkRecordSerializer,
    TechnicianWorkRecordUpdateSerializer,
    TechnicianUserSerializer,
    TechnicianAllocationDraftSerializer,
)

from .models import ServiceManagementRecord, ServiceManagementMaterial
from .serializers import (
    ServiceManagementRecordSerializer, 
    ServiceManagementMaterialSerializer,
    ServiceManagementMaterialCreateSerializer
)

from django.core.exceptions import ValidationError as DjangoValidationError
from inventory.models import InventoryItem
from quotation.models import Quotation, QuotationVersion
from .serializers import QuotationSerializer
from api.models import CustomUser


def _create_technician_work_record(request, service_record, data):
    # Sync edited customer details back to parent ServiceManagementRecord
    updated = False
    if 'customer_name' in data and data['customer_name']:
        service_record.customer_name = data['customer_name']
        updated = True
    if 'customer_phone' in data and data['customer_phone']:
        service_record.customer_contact = data['customer_phone']
        updated = True
    if updated:
        service_record.save()

    payload = {
        'technician': data.get('technician'),
        'service_record': service_record.id,
        'gps_location': data.get('gps_location', ''),
        'work_description': data.get('work_description', ''),
        'work_date': data.get('work_date') or timezone.now().date(),
    }
    if 'payment_amount' in data:
        payload['payment_amount'] = data.get('payment_amount')
    if 'payment_status' in data:
        payload['payment_status'] = data.get('payment_status')
    if 'customer_name' in data:
        payload['customer_name'] = data.get('customer_name')
    if 'customer_phone' in data:
        payload['customer_phone'] = data.get('customer_phone')
    if 'customer_address' in data:
        payload['customer_address'] = data.get('customer_address')

    serializer = TechnicianWorkRecordSerializer(
        data=payload,
        context={'request': request},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def _get_service_record_for_amc_contract(contract):
    customer = contract.customer
    if not customer:
        return None

    qs = ServiceManagementRecord.objects.filter(
        contract_type='amc',
        contract_status='active',
    ).filter(
        Q(customer_id=customer.id) | Q(customer_name__iexact=customer.name)
    )

    if contract.amc_type:
        typed = qs.filter(amc_service_type=contract.amc_type)
        if typed.exists():
            qs = typed

    return qs.order_by('-created_at').first()


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSearchSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'email', 'contact_number']
    pagination_class = None

class QuotationViewSet(viewsets.ModelViewSet):
    serializer_class = QuotationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer']
    search_fields = ['quotation_no', 'customer__name', 'subject']
    
    def get_queryset(self):
        return Quotation.objects.all().prefetch_related(
            Prefetch('versions', queryset=QuotationVersion.objects.prefetch_related(
                'high_side_items__product_variant',
                'low_side_items__item'
            )),
            'customer',
            'site'
        ).select_related('customer', 'site').order_by('-id')

class ServiceManagementRecordViewSet(viewsets.ModelViewSet):
    queryset = ServiceManagementRecord.objects.all()
    serializer_class = ServiceManagementRecordSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['contract_type', 'customer', 'contract_status']
    search_fields = ['customer_name', 'customer_contact', 'subject']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='technician-allocation-draft')
    def technician_allocation_draft(self, request, pk=None):
        """Return auto-filled customer/payment data for technician allocation button."""
        record = self.get_object()
        serializer = TechnicianAllocationDraftSerializer(record)
        data = serializer.data
        data['service_record'] = record.id
        return Response(data)

    @action(detail=True, methods=['post'], url_path='allocate-work-to-technician')
    def allocate_work_to_technician(self, request, pk=None):
        """
        Create a technician work record from this exact service management row.
        Expected body: technician, gps_location?, work_description?, work_date?
        """
        record = self.get_object()
        work_record = _create_technician_work_record(request, record, request.data)
        return Response(
            TechnicianWorkRecordSerializer(work_record).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def add_material(self, request, pk=None):
        """Add material/AC type to service record"""
        record = self.get_object()
        serializer = ServiceManagementMaterialCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            material = ServiceManagementMaterial.objects.create(
                service_record=record,
                ac_type_id=serializer.validated_data['ac_type_id'],
                quantity=serializer.validated_data['quantity'],
                unit=serializer.validated_data['unit'],
                rate=serializer.validated_data['rate'],
                description=serializer.validated_data.get('description', '')
            )
            return Response(
                ServiceManagementMaterialSerializer(material).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='material/(?P<material_id>[^/.]+)')
    def remove_material(self, request, pk=None, material_id=None):
        """Remove material from service record"""
        try:
            material = ServiceManagementMaterial.objects.get(
                id=material_id,
                service_record_id=pk
            )
            material.delete()
            record = self.get_object()
            return Response(
                ServiceManagementRecordSerializer(record).data,
                status=status.HTTP_200_OK
            )
        except ServiceManagementMaterial.DoesNotExist:
            return Response(
                {'error': 'Material not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class ServiceManagementMaterialViewSet(viewsets.ModelViewSet):
    queryset = ServiceManagementMaterial.objects.all()
    serializer_class = ServiceManagementMaterialSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class AMCContractViewSet(viewsets.ModelViewSet):
    queryset = AMCContract.objects.all()
    serializer_class = AMCContractSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer', 'status', 'amc_included_in_sale']
    search_fields = ['contract_number', 'customer__name', 'amc_type']
    
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
        
        if AMCRenewal.objects.filter(previous_contract=contract, status='RENEWED').exists():
            return Response(
                {'error': 'Contract already renewed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_contract = AMCContract.objects.create(
            customer=contract.customer,
            amc_type=contract.amc_type,
            visit_frequency=contract.visit_frequency,
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
        
        AMCRenewal.objects.create(
            previous_contract=contract,
            new_contract=new_contract,
            renewal_date=timezone.now().date(),
            renewal_cost=new_contract.amc_cost,
            status='RENEWED'
        )
        
        serializer = self.get_serializer(new_contract)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def spare_parts(self, request, pk=None):
        contract = self.get_object()
        parts = contract.spare_parts.select_related('inventory_item__item').all()
        return Response(AMCSparePartSerializer(parts, many=True).data)

    @action(detail=True, methods=['post'])
    def add_spare_part(self, request, pk=None):
        contract = self.get_object()
        if contract.amc_type != 'NON_COMPREHENSIVE':
            return Response(
                {'detail': 'Spare parts billing applies only to Non-Comprehensive AMC contracts.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        inventory_item_id = request.data.get('inventory_item')
        quantity = request.data.get('quantity_used') or request.data.get('quantity')
        rate = request.data.get('rate_per_unit') or request.data.get('rate')

        try:
            inv_item = InventoryItem.objects.get(id=inventory_item_id)
        except InventoryItem.DoesNotExist:
            return Response({'detail': 'Inventory item not found.'}, status=status.HTTP_400_BAD_REQUEST)

        if inv_item.product_variant_id is not None:
            return Response(
                {'detail': 'Only low-side materials can be added as spare parts.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            part = AMCSparePart.objects.create(
                amc_contract=contract,
                inventory_item_id=inventory_item_id,
                quantity_used=quantity,
                unit=request.data.get('unit', 'Nos'),
                rate_per_unit=rate,
                gst_percent=request.data.get('gst_percent', 18),
                hsn_sac=request.data.get('hsn_sac', ''),
                description=request.data.get('description', ''),
            )
        except (DjangoValidationError, Exception) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AMCSparePartSerializer(part).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='spare_parts/(?P<part_id>[^/.]+)')
    def remove_spare_part(self, request, pk=None, part_id=None):
        contract = self.get_object()
        try:
            part = AMCSparePart.objects.get(id=part_id, amc_contract=contract)
        except AMCSparePart.DoesNotExist:
            return Response({'detail': 'Spare part not found.'}, status=status.HTTP_404_NOT_FOUND)

        if part.invoice_id:
            return Response(
                {'detail': 'Cannot remove spare parts that are already invoiced.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        part.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def invoice_draft(self, request, pk=None):
        contract = self.get_object()
        if contract.amc_type != 'NON_COMPREHENSIVE':
            return Response(
                {'detail': 'Invoice draft is only for Non-Comprehensive AMC contracts.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        parts = contract.spare_parts.filter(invoice__isnull=True).select_related(
            'inventory_item__item'
        )
        if not parts.exists():
            return Response(
                {'detail': 'No uninvoiced spare parts found for this contract.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer = contract.customer
        low_side_items = []
        spare_part_ids = []

        for part in parts:
            item = part.inventory_item.item
            spare_part_ids.append(part.id)
            low_side_items.append({
                'item': item.id,
                'item_code': item.item_code,
                'description': part.description or item.item_code,
                'hsn_sac': part.hsn_sac or getattr(item, 'hsn_sac', '') or '',
                'gst_percent': float(part.gst_percent),
                'quantity': float(part.quantity_used),
                'unit': part.unit,
                'rate': float(part.rate_per_unit),
            })

        return Response({
            'amc_contract_id': contract.id,
            'contract_number': contract.contract_number,
            'spare_part_ids': spare_part_ids,
            'customer_id': customer.id,
            'customer_name': customer.name,
            'customer_phone': customer.contact_number or '',
            'buyer_address': customer.address or '',
            'buyer_gstin': customer.gst or '',
            'buyer_state': customer.state or '',
            'work_description': f'AMC Spare Parts - {contract.contract_number}',
            'low_side_items': low_side_items,
        })

    @action(detail=True, methods=['post'])
    def mark_spare_parts_invoiced(self, request, pk=None):
        contract = self.get_object()
        invoice_id = request.data.get('invoice_id')
        spare_part_ids = request.data.get('spare_part_ids', [])

        if not invoice_id:
            return Response({'detail': 'invoice_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        updated = contract.spare_parts.filter(
            id__in=spare_part_ids,
            invoice__isnull=True
        ).update(invoice_id=invoice_id)

        return Response({'updated': updated})

    @action(detail=True, methods=['get'], url_path='technician-allocation-draft')
    def technician_allocation_draft(self, request, pk=None):
        """Return auto-filled customer/payment data for technician allocation."""
        contract = self.get_object()
        service_record = _get_service_record_for_amc_contract(contract)

        if service_record:
            serializer = TechnicianAllocationDraftSerializer(service_record)
            data = serializer.data
            data['service_record'] = service_record.id
            return Response(data)

        customer = contract.customer
        address_parts = [
            customer.address,
            customer.city,
            customer.state,
            customer.pin_code,
        ]
        return Response({
            'service_record': None,
            'customer': customer.id,
            'customer_name': customer.name,
            'customer_phone': customer.contact_number or '',
            'customer_address': ', '.join(part for part in address_parts if part),
            'payment_amount': contract.amc_cost,
        })

    @action(detail=True, methods=['post'], url_path='allocate-work-to-technician')
    def allocate_work_to_technician(self, request, pk=None):
        """Create a technician work record for this AMC contract."""
        contract = self.get_object()
        service_record = _get_service_record_for_amc_contract(contract)
        if not service_record:
            return Response(
                {
                    'detail': (
                        'No active AMC service management record found for this customer. '
                        'Please create one in Service Management first.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        work_record = _create_technician_work_record(request, service_record, request.data)
        return Response(
            TechnicianWorkRecordSerializer(work_record).data,
            status=status.HTTP_201_CREATED,
        )


class AMCRenewalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AMCRenewal.objects.all()
    serializer_class = AMCRenewalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']


class TechnicianWorkRecordViewSet(viewsets.ModelViewSet):
    queryset = TechnicianWorkRecord.objects.select_related(
        'technician', 'service_record'
    ).all()
    serializer_class = TechnicianWorkRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['technician', 'service_record', 'work_date']
    search_fields = ['customer_name', 'customer_phone', 'work_description']

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return TechnicianWorkRecordUpdateSerializer
        return TechnicianWorkRecordSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        return Response(TechnicianWorkRecordSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='technicians')
    def technicians(self, request):
        technicians = CustomUser.objects.select_related('role').filter(
            role__name__iexact='technician',
            is_active=True,
        ).order_by('first_name', 'last_name', 'email')
        return Response(TechnicianUserSerializer(technicians, many=True).data)
