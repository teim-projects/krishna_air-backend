from rest_framework import serializers
from .models import Vendor , TermsConditionType , TermsConditions , PurchaseOrder, PurchaseOrderProduct
from .service import create_new_po_version

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'
    
    def validate_mobile(self, value):
        """Validate mobile number is 10 digits"""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be 10 digits")
        return value
    
    def validate_gst_details(self, value):
        """Validate GST number is 15 characters"""
        if len(value) != 15:
            raise serializers.ValidationError("GST number must be 15 characters")
        return value
    
    def validate_pan_details(self, value):
        """Validate PAN number is 10 characters"""
        if value and len(value) != 10:
            raise serializers.ValidationError("PAN number must be 10 characters")
        return value
    
    def validate_office_poc_phone(self, value):
        """Validate office POC phone is 10 digits"""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Phone number must be 10 digits")
        return value



# --------------------------------------------------------------------------------
# Terms Condition Serializers
# --------------------------------------------------------------------------------

class TermsConditionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsConditionType
        fields = "__all__"

class TermsConditionsSerializer(serializers.ModelSerializer):
    terms_condition_type_name = serializers.CharField(
        source="terms_condition_type.name",
        read_only=True
    )

    class Meta:
        model = TermsConditions
        fields = "__all__"


class PurchaseOrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderProduct
        fields = "__all__"
        read_only_fields = ("amount","purchase_order")


class PurchaseOrderSerializer(serializers.ModelSerializer):
    products = PurchaseOrderProductSerializer(many=True)
    terms_conditions = serializers.PrimaryKeyRelatedField(
        queryset=TermsConditions.objects.all(),
        many=True,
        required=False,
        write_only=True

    )

    terms_conditions_details = TermsConditionsSerializer(
        source="terms_conditions",
        many=True,
        read_only=True
    )

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ("purchase_order_no","version", "is_current")

    def create(self, validated_data):
        products_data = validated_data.pop("products", [])
        terms_conditions = validated_data.pop("terms_conditions", [])

        po = PurchaseOrder.objects.create(**validated_data)

        if terms_conditions:
            po.terms_conditions.set(terms_conditions)

        for p in products_data:
            PurchaseOrderProduct.objects.create(purchase_order=po, **p)

        return po

    def update(self, instance, validated_data):
        if not instance.is_current:
            raise serializers.ValidationError("Old PO versions cannot be edited.")

        products_data = validated_data.pop("products", [])
        terms_conditions = validated_data.pop("terms_conditions", None)

        new_po = create_new_po_version(instance, validated_data, products_data)

        # ✅ Only set M2M if user sent it
        if terms_conditions is not None:
            new_po.terms_conditions.set(terms_conditions)

        return new_po