from rest_framework import viewsets, status, mixins, filters
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch, Q
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models import CustomUser
from api.permissions import HasDocPermission

from .models import (
    Customer,
    AMCContract,
    AMCRenewal,
    AMCSparePart,
    TechnicianWorkRecord,
    AMCServiceVisit,
    ServiceManagementRecord,
    ServiceManagementMaterial,
)
from .serializers import (
    CustomerSearchSerializer,
    AMCContractSerializer,
    AMCRenewalSerializer,
    AMCSparePartSerializer,
    TechnicianWorkRecordSerializer,
    TechnicianWorkRecordUpdateSerializer,
    TechnicianUserSerializer,
    TechnicianAllocationDraftSerializer,
    AMCServiceVisitSerializer,
    AMCServiceVisitUpdateSerializer,
    ServiceManagementRecordSerializer,
    ServiceManagementMaterialSerializer,
    ServiceManagementMaterialCreateSerializer,
    QuotationSerializer,
)
from .visit_service import (
    get_service_record_for_amc_contract,
    sync_amc_service_visits,
    close_amc_contract_if_all_visits_completed,
)

from django.core.exceptions import ValidationError as DjangoValidationError
from inventory.models import InventoryItem
from quotation.models import Quotation, QuotationVersion


def _get_service_record_for_amc_contract(contract):
    return get_service_record_for_amc_contract(contract)


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


def _attach_service_record_to_amc_visits(record):
    """When an AMC service management row is saved, link it to open planned visits."""
    if record.contract_type != 'amc' or not record.customer_id:
        return
    AMCServiceVisit.objects.filter(
        amc_contract__customer_id=record.customer_id,
        service_record__isnull=True,
        technician_work_record__isnull=True,
    ).update(service_record=record)


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
    document_type = "Service Management"
    permission_classes = [IsAuthenticated, HasDocPermission]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['contract_type', 'customer', 'contract_status']
    search_fields = ['customer_name', 'customer_contact', 'subject']
    
    def perform_create(self, serializer):
        record = serializer.save(created_by=self.request.user)
        _attach_service_record_to_amc_visits(record)

    def perform_update(self, serializer):
        record = serializer.save()
        _attach_service_record_to_amc_visits(record)

    def destroy(self, request, *args, **kwargs):
        """
        AMC service records are never hard-deleted.
        Delete button sets status to inactive instead.
        One Time / Warranty records can still be hard-deleted.
        """
        record = self.get_object()
        if record.contract_type == 'amc':
            if record.contract_status == 'closed':
                return Response(
                    {'detail': 'Closed AMC service records cannot be deleted or deactivated.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            record.contract_status = 'inactive'
            record.save(update_fields=['contract_status', 'updated_at'])
            return Response(
                ServiceManagementRecordSerializer(record).data,
                status=status.HTTP_200_OK,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='mark-closed')
    def mark_closed(self, request, pk=None):
        """Mark service as completed/closed."""
        record = self.get_object()
        record.contract_status = 'closed'
        record.save(update_fields=['contract_status', 'updated_at'])
        return Response(ServiceManagementRecordSerializer(record).data)

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
    document_type = "Service Management"
    permission_classes = [IsAuthenticated, HasDocPermission]
    pagination_class = None


class AMCContractViewSet(viewsets.ModelViewSet):
    queryset = AMCContract.objects.all()
    serializer_class = AMCContractSerializer
    document_type = "AMC"
    permission_classes = [IsAuthenticated, HasDocPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer', 'status', 'amc_included_in_sale']
    search_fields = ['contract_number', 'customer__name', 'amc_type']

    def perform_create(self, serializer):
        contract = serializer.save()
        # Backend safeguard: always sync planned visits after contract save.
        sync_amc_service_visits(contract)

    def perform_update(self, serializer):
        contract = serializer.save()
        # Backend safeguard: always sync planned visits after contract save.
        sync_amc_service_visits(contract)

    def destroy(self, request, *args, **kwargs):
        """
        AMC contracts are never hard-deleted.
        Delete button sets status to INACTIVE instead.
        """
        contract = self.get_object()
        if contract.status == 'CLOSED':
            return Response(
                {'detail': 'Closed AMC contracts cannot be deleted or deactivated.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        contract.status = 'INACTIVE'
        contract.save(update_fields=['status', 'updated_at'])
        return Response(
            AMCContractSerializer(contract).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='mark-closed')
    def mark_closed(self, request, pk=None):
        """Mark AMC contract as completed/closed."""
        contract = self.get_object()
        contract.status = 'CLOSED'
        contract.save(update_fields=['status', 'updated_at'])
        return Response(AMCContractSerializer(contract).data)
    
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
            total_visit_count=contract.total_visit_count,
            schedule_note=contract.schedule_note,
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

        sync_amc_service_visits(new_contract)
        
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

    @action(detail=True, methods=['get'], url_path='service-visits')
    def service_visits(self, request, pk=None):
        """List auto-generated AMC service visits for this contract."""
        contract = self.get_object()
        if not contract.service_visits.exists():
            sync_amc_service_visits(contract)
        visits = contract.service_visits.select_related(
            'service_record',
            'technician_work_record__technician',
        )
        return Response(AMCServiceVisitSerializer(visits, many=True).data)


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
    document_type = "Service Management"
    permission_classes = [IsAuthenticated, HasDocPermission]
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


class AMCServiceVisitViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Planned AMC visits (auto-created with the contract).
    Use allocate-work-to-technician to create the existing TechnicianWorkRecord flow.
    """
    queryset = AMCServiceVisit.objects.select_related(
        'amc_contract',
        'amc_contract__customer',
        'service_record',
        'technician_work_record__technician',
    ).all()
    document_type = "AMC"
    permission_classes = [IsAuthenticated, HasDocPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['amc_contract', 'status']

    def list(self, request, *args, **kwargs):
        amc_contract_id = request.query_params.get('amc_contract')
        if amc_contract_id:
            try:
                contract = AMCContract.objects.get(pk=amc_contract_id)
                if not contract.service_visits.exists():
                    sync_amc_service_visits(contract)
            except (AMCContract.DoesNotExist, ValueError):
                pass
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return AMCServiceVisitUpdateSerializer
        return AMCServiceVisitSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        instance.refresh_from_db()
        return Response(AMCServiceVisitSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='technician-allocation-draft')
    def technician_allocation_draft(self, request, pk=None):
        """Prefill data for Assign Technician modal for one planned visit."""
        visit = self.get_object()
        contract = visit.amc_contract
        service_record = visit.service_record or get_service_record_for_amc_contract(contract)

        if service_record:
            data = TechnicianAllocationDraftSerializer(service_record).data
            data['service_record'] = service_record.id
        else:
            customer = contract.customer
            address_parts = [
                customer.address,
                customer.city,
                customer.state,
                customer.pin_code,
            ]
            data = {
                'service_record': None,
                'customer': customer.id,
                'customer_name': customer.name,
                'customer_phone': customer.contact_number or '',
                'customer_address': ', '.join(part for part in address_parts if part),
            }

        # Per-visit share of AMC cost (not full amc_cost)
        data['payment_amount'] = visit.amount
        data['amc_service_visit_id'] = visit.id
        data['visit_number'] = visit.visit_number
        data['planned_date'] = visit.planned_date.isoformat()
        data['work_description'] = visit.work_description or ''
        data['amount'] = visit.amount
        return Response(data)

    @action(detail=True, methods=['post'], url_path='allocate-work-to-technician')
    def allocate_work_to_technician(self, request, pk=None):
        """Create TechnicianWorkRecord and link it to this planned visit."""
        visit = self.get_object()
        if visit.technician_work_record_id:
            return Response(
                {'detail': 'This visit is already allocated to a technician.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service_record = visit.service_record or get_service_record_for_amc_contract(visit.amc_contract)
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

        payload = dict(request.data)
        payload['work_date'] = payload.get('work_date') or visit.planned_date
        payload['work_description'] = payload.get('work_description', visit.work_description or '')
        if 'payment_amount' not in payload or payload.get('payment_amount') in (None, ''):
            payload['payment_amount'] = visit.amount

        work_record = _create_technician_work_record(request, service_record, payload)

        visit.technician_work_record = work_record
        visit.service_record = service_record
        visit.status = AMCServiceVisit.STATUS_ASSIGNED
        if payload.get('work_description'):
            visit.work_description = payload['work_description']
        visit.save(update_fields=[
            'technician_work_record',
            'service_record',
            'status',
            'work_description',
            'updated_at',
        ])

        return Response(
            {
                'visit': AMCServiceVisitSerializer(visit).data,
                'work_record': TechnicianWorkRecordSerializer(work_record).data,
            },
            status=status.HTTP_201_CREATED,
        )


def _technician_display_name(user):
    if not user:
        return '—'
    full = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full or user.email or user.mobile_no or f"User {user.id}"


def _completion_date_for_work(work_record):
    if work_record.work_date:
        return work_record.work_date.isoformat()
    return work_record.updated_at.date().isoformat()


def _work_description_for_record(work_record):
    visit = getattr(work_record, 'amc_service_visit', None)
    if visit and visit.work_description:
        return visit.work_description
    return work_record.work_description or ''


def _service_address_for_contract(contract):
    service = get_service_record_for_amc_contract(contract)
    if not service and contract.customer_id:
        service = (
            ServiceManagementRecord.objects.filter(
                contract_type='amc',
            )
            .filter(
                Q(customer_id=contract.customer_id)
                | Q(customer_name__iexact=contract.customer.name)
            )
            .order_by('-updated_at')
            .first()
        )
    if service and service.address:
        return service.address
    customer = contract.customer
    if customer:
        return customer.site_address or customer.address or ''
    return ''


class CompletedWorkListView(APIView):
    """Completed technician jobs, closed one-time/warranty services, and closed AMC contracts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = []

        works = (
            TechnicianWorkRecord.objects.filter(payment_status='completed')
            .select_related('technician', 'service_record', 'amc_service_visit')
            .order_by('-updated_at')
        )
        for work in works:
            items.append({
                'id': f'w-{work.id}',
                'kind': 'service',
                'contract_type': getattr(work.service_record, 'contract_type', None),
                'customer_name': work.customer_name,
                'technician_name': _technician_display_name(work.technician),
                'completion_date': _completion_date_for_work(work),
            })

        # Closed one-time / warranty service management records (service provided)
        closed_services = (
            ServiceManagementRecord.objects.filter(
                contract_status='closed',
                contract_type__in=['one_time', 'warranty'],
            )
            .prefetch_related(
                Prefetch(
                    'technician_work_records',
                    queryset=TechnicianWorkRecord.objects.select_related('technician').order_by(
                        '-work_date', '-updated_at'
                    ),
                )
            )
            .order_by('-updated_at')
        )
        for service in closed_services:
            works_for_service = list(service.technician_work_records.all())
            tech_name = '—'
            if works_for_service:
                tech_name = _technician_display_name(works_for_service[0].technician)
            items.append({
                'id': f's-{service.id}',
                'kind': 'one_time_service',
                'contract_type': service.contract_type,
                'customer_name': service.customer_name,
                'technician_name': tech_name,
                'completion_date': (
                    service.service_end_date.isoformat()
                    if service.service_end_date
                    else service.updated_at.date().isoformat()
                ),
            })

        completed_visits_prefetch = Prefetch(
            'service_visits',
            queryset=AMCServiceVisit.objects.filter(
                status=AMCServiceVisit.STATUS_COMPLETED,
            ).select_related(
                'technician_work_record__technician',
            ).order_by('-updated_at'),
        )
        contracts = (
            AMCContract.objects.filter(status='CLOSED')
            .select_related('customer')
            .prefetch_related(completed_visits_prefetch)
            .order_by('-updated_at')
        )
        for contract in contracts:
            visits = list(contract.service_visits.all())
            tech_name = '—'
            if visits:
                wr = visits[0].technician_work_record
                if wr:
                    tech_name = _technician_display_name(wr.technician)
            items.append({
                'id': f'c-{contract.id}',
                'kind': 'amc_contract',
                'contract_type': 'amc',
                'customer_name': contract.customer.name if contract.customer_id else '—',
                'technician_name': tech_name,
                'completion_date': contract.updated_at.date().isoformat(),
            })

        items.sort(key=lambda row: row['completion_date'], reverse=True)
        return Response(items)


class CompletedWorkDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        if item_id.startswith('w-'):
            try:
                pk = int(item_id[2:])
            except ValueError:
                return Response({'detail': 'Invalid id.'}, status=status.HTTP_400_BAD_REQUEST)
            work = (
                TechnicianWorkRecord.objects.filter(pk=pk, payment_status='completed')
                .select_related('technician', 'service_record', 'amc_service_visit')
                .first()
            )
            if not work:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            visit = getattr(work, 'amc_service_visit', None)
            status_label = 'Completed'
            if visit:
                status_label = visit.get_status_display()
            return Response({
                'id': item_id,
                'kind': 'service',
                'contract_type': getattr(work.service_record, 'contract_type', None),
                'customer_name': work.customer_name,
                'technician_name': _technician_display_name(work.technician),
                'technician_mobile': work.technician.mobile_no or '',
                'work_description': _work_description_for_record(work),
                'work_address': work.customer_address,
                'status': status_label,
                'completion_date': _completion_date_for_work(work),
                'technician_assigned': _technician_display_name(work.technician),
            })

        if item_id.startswith('s-'):
            try:
                pk = int(item_id[2:])
            except ValueError:
                return Response({'detail': 'Invalid id.'}, status=status.HTTP_400_BAD_REQUEST)
            service = (
                ServiceManagementRecord.objects.filter(
                    pk=pk,
                    contract_status='closed',
                    contract_type__in=['one_time', 'warranty'],
                )
                .prefetch_related(
                    Prefetch(
                        'technician_work_records',
                        queryset=TechnicianWorkRecord.objects.select_related('technician').order_by(
                            'work_date', 'id'
                        ),
                    )
                )
                .first()
            )
            if not service:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

            works_for_service = list(service.technician_work_records.all())
            descriptions = [
                w.work_description.strip()
                for w in works_for_service
                if w.work_description and w.work_description.strip()
            ]
            work_description = '\n'.join(descriptions) if descriptions else (service.subject or '—')
            techs = []
            for w in works_for_service:
                name = _technician_display_name(w.technician)
                if name not in techs:
                    techs.append(name)
            lead = works_for_service[-1] if works_for_service else None
            lead_user = lead.technician if lead else None
            completion = (
                service.service_end_date.isoformat()
                if service.service_end_date
                else service.updated_at.date().isoformat()
            )
            if lead:
                completion = _completion_date_for_work(lead)

            return Response({
                'id': item_id,
                'kind': 'one_time_service',
                'contract_type': service.contract_type,
                'customer_name': service.customer_name,
                'technician_name': _technician_display_name(lead_user),
                'technician_mobile': (lead_user.mobile_no or '') if lead_user else '',
                'work_description': work_description,
                'work_address': service.address or '',
                'status': service.get_contract_status_display(),
                'completion_date': completion,
                'technician_assigned': ', '.join(techs) if techs else '—',
            })

        if item_id.startswith('c-'):
            try:
                pk = int(item_id[2:])
            except ValueError:
                return Response({'detail': 'Invalid id.'}, status=status.HTTP_400_BAD_REQUEST)
            contract = (
                AMCContract.objects.filter(pk=pk, status='CLOSED')
                .select_related('customer')
                .prefetch_related(
                    Prefetch(
                        'service_visits',
                        queryset=AMCServiceVisit.objects.filter(
                            status=AMCServiceVisit.STATUS_COMPLETED,
                        ).select_related('technician_work_record__technician').order_by('visit_number'),
                    )
                )
                .first()
            )
            if not contract:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

            visits = list(contract.service_visits.all())
            if visits:
                work_description = '\n'.join(
                    f"Visit {v.visit_number}: {v.work_description.strip()}"
                    for v in visits
                    if v.work_description and v.work_description.strip()
                )
            else:
                work_description = ''
            if not work_description:
                work_description = (
                    f"AMC contract {contract.contract_number} — all scheduled visits completed."
                )

            techs = []
            for v in visits:
                wr = v.technician_work_record
                if wr:
                    name = _technician_display_name(wr.technician)
                    if name not in techs:
                        techs.append(name)
            technician_assigned = ', '.join(techs) if techs else '—'
            last_wr = visits[-1].technician_work_record if visits else None
            lead_user = last_wr.technician if last_wr else None

            return Response({
                'id': item_id,
                'kind': 'amc_contract',
                'contract_type': 'amc',
                'customer_name': contract.customer.name if contract.customer_id else '—',
                'contract_number': contract.contract_number,
                'technician_name': _technician_display_name(lead_user),
                'technician_mobile': (lead_user.mobile_no or '') if lead_user else '',
                'work_description': work_description,
                'work_address': _service_address_for_contract(contract),
                'status': contract.get_status_display(),
                'completion_date': contract.updated_at.date().isoformat(),
                'technician_assigned': technician_assigned,
            })

        return Response({'detail': 'Invalid id.'}, status=status.HTTP_400_BAD_REQUEST)
