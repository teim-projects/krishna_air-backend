from rest_framework import serializers
from .models import (
    AMCPackage, AMCContract, AMCService, 
    AMCServiceParts, AMCServiceLabor, AMCInvoice, AMCRenewal
)

class AMCPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMCPackage
        fields = '__all__'


class AMCServicePartsSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AMCServiceParts
        fields = ['id', 'inventory_item', 'product_name', 'quantity_used', 'rate_per_unit', 'total_cost', 'include_in_customer_invoice']

    def get_product_name(self, obj):
        if not obj.inventory_item:
            return "Unknown"
        if obj.inventory_item.product_variant:
            sku = obj.inventory_item.product_variant.sku
            model_no = getattr(getattr(obj.inventory_item.product_variant, 'product_model', None), 'model_no', '')
            return f"{sku} {model_no}".strip()
        if obj.inventory_item.item:
            return obj.inventory_item.item.item_code
        return "Unknown"


class AMCServiceLaborSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMCServiceLabor
        fields = '__all__'


class AMCServiceSerializer(serializers.ModelSerializer):
    parts_used = AMCServicePartsSerializer(many=True, read_only=True)
    labor = AMCServiceLaborSerializer(read_only=True)
    
    class Meta:
        model = AMCService
        fields = '__all__'


class AMCInvoiceSerializer(serializers.ModelSerializer):
    service_details = AMCServiceSerializer(source='service', read_only=True)
    
    class Meta:
        model = AMCInvoice
        fields = '__all__'
        read_only_fields = ['invoice_number', 'subtotal', 'gst_amount', 'total_amount']


class AMCContractSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source='package.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    product_name = serializers.CharField(source='product_variant.product_model.model_no', read_only=True)
    services = AMCServiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = AMCContract
        fields = '__all__'
        read_only_fields = ['contract_number']


class AMCRenewalSerializer(serializers.ModelSerializer):
    previous_contract = AMCContractSerializer(read_only=True)
    new_contract = AMCContractSerializer(read_only=True)
    
    class Meta:
        model = AMCRenewal
        fields = '__all__'
