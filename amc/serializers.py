from rest_framework import serializers
from .models import (
    AMCContract, AMCRenewal, AMCSparePart, TechnicianWorkRecord,
    ServiceManagementRecord, ServiceManagementMaterial
)
from lead_management.models import Customer
from api.models import CustomUser

# Import Quotation serializers from quotation app
from quotation.serializers import (
    QuotationHighSideItemSerializer,
    QuotationLowSideItemSerializer,
    QuotationVersionSerializer as QuotationVersionSerializerBase,
    QuotationSerializer as QuotationSerializerBase
)
from quotation.models import Quotation, QuotationVersion


class CustomerSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'contact_number', 'address', 'city', 'state', 'pin_code']


# ===== QUOTATION INTEGRATION SERIALIZERS =====
class QuotationVersionSerializer(serializers.ModelSerializer):
    high_side_items = QuotationHighSideItemSerializer(many=True, read_only=True)
    low_side_items = QuotationLowSideItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuotationVersion
        fields = [
            'id', 'quotation', 'version_no', 'created_at', 'is_active',
            'high_side_items', 'low_side_items',
            'subject', 'gst_percentage', 'gst_type', 'subtotal', 'gst_amount', 'total_amount'
        ]


class QuotationSerializer(serializers.ModelSerializer):
    versions = QuotationVersionSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_id = serializers.IntegerField(source='customer.id', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True, allow_null=True)
    site_address = serializers.CharField(source='site.address', read_only=True, allow_null=True)
    site_city = serializers.CharField(source='site.city', read_only=True, allow_null=True)
    site_state = serializers.CharField(source='site.state', read_only=True, allow_null=True)
    site_pincode = serializers.CharField(source='site.pincode', read_only=True, allow_null=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'quotation_date', 'customer', 'customer_name', 'customer_id',
            'site', 'site_name', 'site_address', 'site_city', 'site_state', 'site_pincode',
            'subject', 'gst_percentage', 'versions'
        ]


# ===== SERVICE MANAGEMENT SERIALIZERS =====
class ServiceManagementMaterialSerializer(serializers.ModelSerializer):
    ac_type_code = serializers.CharField(source='ac_type.item_code', read_only=True)
    
    class Meta:
        model = ServiceManagementMaterial
        fields = ['id', 'ac_type', 'ac_type_code', 'quantity', 'unit', 'rate', 'amount', 'description']


class ServiceManagementRecordSerializer(serializers.ModelSerializer):
    materials = ServiceManagementMaterialSerializer(many=True, read_only=True)
    assigned_technicians = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceManagementRecord
        fields = [
            'id', 'customer', 'customer_contact', 'customer_name', 'customer_email', 'subject',
            'contract_type', 'contract_status', 'amc_service_type', 'segment',
            'service_start_date', 'service_end_date',
            'state', 'city', 'pincode', 'address',
            'apply_gst', 'gst_percentage', 'total_price_without_gst', 
            'gst_amount', 'total_price_with_gst', 'materials',
            'assigned_technicians',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['gst_amount', 'total_price_with_gst', 'created_at', 'updated_at']

    def get_assigned_technicians(self, obj):
        records = obj.technician_work_records.select_related('technician').all()
        return [
            {
                'id': r.technician.id,
                'name': f"{r.technician.first_name or ''} {r.technician.last_name or ''}".strip() or r.technician.email,
                'email': r.technician.email,
                'work_date': r.work_date.isoformat() if r.work_date else None,
                'work_description': r.work_description,
            }
            for r in records
        ]
    
    def create(self, validated_data):
        record = ServiceManagementRecord.objects.create(**validated_data)
        record.calculate_totals()
        record.save()
        return record
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.calculate_totals()
        instance.save()
        return instance


class ServiceManagementMaterialCreateSerializer(serializers.ModelSerializer):
    ac_type_id = serializers.IntegerField()
    
    class Meta:
        model = ServiceManagementMaterial
        fields = ['ac_type_id', 'quantity', 'unit', 'rate', 'description']


# ===== AMC SERIALIZERS =====
class AMCSparePartSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    item_id = serializers.IntegerField(source='inventory_item.item_id', read_only=True)
    stock_available = serializers.DecimalField(
        source='inventory_item.quantity', max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = AMCSparePart
        fields = [
            'id', 'amc_contract', 'inventory_item', 'item_id', 'product_name',
            'quantity_used', 'unit', 'rate_per_unit', 'gst_percent', 'hsn_sac',
            'description', 'total_cost', 'invoice', 'stock_available', 'created_at'
        ]
        read_only_fields = ['total_cost', 'invoice', 'created_at']

    def get_product_name(self, obj):
        if obj.inventory_item and obj.inventory_item.item:
            return obj.inventory_item.item.item_code
        return 'Unknown'


class AMCContractSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    product_name = serializers.CharField(source='product_variant.product_model.model_no', read_only=True)
    spare_parts_count = serializers.SerializerMethodField()
    uninvoiced_spare_parts_count = serializers.SerializerMethodField()
    customer_phone = serializers.CharField(source='customer.contact_number', read_only=True)
    service_record_id = serializers.SerializerMethodField()

    class Meta:
        model = AMCContract
        fields = '__all__'
        read_only_fields = ['contract_number']

    def get_spare_parts_count(self, obj):
        return obj.spare_parts.count()

    def get_uninvoiced_spare_parts_count(self, obj):
        return obj.spare_parts.filter(invoice__isnull=True).count()

    def get_service_record_id(self, obj):
        from django.db.models import Q
        from .models import ServiceManagementRecord
        customer = obj.customer
        if not customer:
            return None

        qs = ServiceManagementRecord.objects.filter(
            contract_type='amc',
            contract_status='active',
        ).filter(
            Q(customer_id=customer.id) | Q(customer_name__iexact=customer.name)
        )

        if obj.amc_type:
            typed = qs.filter(amc_service_type=obj.amc_type)
            if typed.exists():
                qs = typed

        rec = qs.order_by('-created_at').first()
        return rec.id if rec else None


class AMCRenewalSerializer(serializers.ModelSerializer):
    previous_contract = AMCContractSerializer(read_only=True)
    new_contract = AMCContractSerializer(read_only=True)
    
    class Meta:
        model = AMCRenewal
        fields = '__all__'


class TechnicianUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'display_name', 'email', 'mobile_no']

    def get_display_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        if full_name:
            return full_name
        return obj.email or obj.mobile_no or f"User {obj.id}"


class TechnicianWorkRecordSerializer(serializers.ModelSerializer):
    technician_name = serializers.SerializerMethodField(read_only=True)
    service_customer_name = serializers.CharField(
        source='service_record.customer_name', read_only=True
    )
    service_end_date = serializers.DateField(
        source='service_record.service_end_date', read_only=True
    )

    class Meta:
        model = TechnicianWorkRecord
        fields = [
            'id',
            'technician',
            'technician_name',
            'service_record',
            'service_customer_name',
            'service_end_date',
            'customer_name',
            'customer_phone',
            'customer_address',
            'payment_amount',
            'payment_status',
            'payment_status',
            'gps_location',
            'work_description',
            'work_date',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_by',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'customer_name': {'required': False},
            'customer_phone': {'required': False},
            'customer_address': {'required': False},
        }

    def get_technician_name(self, obj):
        full_name = f"{obj.technician.first_name or ''} {obj.technician.last_name or ''}".strip()
        if full_name:
            return full_name
        return obj.technician.email or obj.technician.mobile_no or f"User {obj.technician_id}"

    def validate_technician(self, value):
        role_name = (value.role.name if value.role else '').strip().lower()
        if role_name != 'technician':
            raise serializers.ValidationError("Selected user is not a technician.")
        return value

    def _autofill_customer_fields(self, validated_data):
        service_record = validated_data['service_record']
        if 'customer_name' not in validated_data or not validated_data['customer_name']:
            validated_data['customer_name'] = service_record.customer_name or ''
        if 'customer_phone' not in validated_data or not validated_data['customer_phone']:
            validated_data['customer_phone'] = service_record.customer_contact or ''
        if 'customer_address' not in validated_data or not validated_data['customer_address']:
            validated_data['customer_address'] = service_record.address or ''
        if 'payment_amount' not in validated_data:
            validated_data['payment_amount'] = service_record.total_price_with_gst or 0
        return validated_data

    def _close_service_if_completed(self, work_record):
        """When technician work is completed, mark linked AMC service as closed."""
        if work_record.payment_status != 'completed':
            return
        service = work_record.service_record
        if service and service.contract_type == 'amc' and service.contract_status != 'closed':
            service.contract_status = 'closed'
            service.save(update_fields=['contract_status', 'updated_at'])

    def create(self, validated_data):
        validated_data = self._autofill_customer_fields(validated_data)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        work_record = super().create(validated_data)
        self._close_service_if_completed(work_record)
        return work_record

    def update(self, instance, validated_data):
        if 'service_record' in validated_data:
            validated_data = self._autofill_customer_fields(validated_data)
        work_record = super().update(instance, validated_data)
        self._close_service_if_completed(work_record)
        return work_record


class TechnicianWorkRecordUpdateSerializer(serializers.ModelSerializer):
    """Edit form: technician, visit date, and remark (work_description)."""
    visit_date = serializers.DateField(source='work_date', required=False)

    class Meta:
        model = TechnicianWorkRecord
        fields = ['technician', 'work_date', 'visit_date', 'work_description']

    def validate_technician(self, value):
        role_name = (value.role.name if value.role else '').strip().lower()
        if role_name != 'technician':
            raise serializers.ValidationError("Selected user is not a technician.")
        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Provide at least one field to update: technician, visit_date, or work_description."
            )
        return attrs

    def update(self, instance, validated_data):
        work_record = super().update(instance, validated_data)
        if work_record.payment_status == 'completed':
            service = work_record.service_record
            if service and service.contract_type == 'amc' and service.contract_status != 'closed':
                service.contract_status = 'closed'
                service.save(update_fields=['contract_status', 'updated_at'])
        return work_record


class TechnicianAllocationDraftSerializer(serializers.ModelSerializer):
    payment_amount = serializers.DecimalField(
        source='total_price_with_gst',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    customer_phone = serializers.CharField(source='customer_contact', read_only=True)
    customer_address = serializers.CharField(source='address', read_only=True)

    class Meta:
        model = ServiceManagementRecord
        fields = [
            'id',
            'customer',
            'customer_name',
            'customer_phone',
            'customer_address',
            'payment_amount',
        ]
