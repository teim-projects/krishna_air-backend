from rest_framework import serializers
from .models import *
from .service import create_new_po_version
from django.db import transaction
from django.db.models import Sum, F

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
    
    # def validate_office_poc_phone(self, value):
    #     """Validate office POC phone is 10 digits"""
    #     if not value.isdigit() or len(value) != 10:
    #         raise serializers.ValidationError("Phone number must be 10 digits")
    #     return value



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



class TermsConditionsBulkSerializer(serializers.Serializer):
    terms_condition_type = serializers.IntegerField()
    terms = serializers.ListField(
        child=serializers.CharField()
    )

    def create(self, validated_data):
        terms_type = validated_data["terms_condition_type"]
        terms_list = validated_data["terms"]

        objects = []

        for term in terms_list:
            obj = TermsConditions.objects.create(
                terms_condition_type_id=terms_type,
                terms=term
            )
            objects.append(obj)

        return objects

class PurchaseOrderProductSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(
        source="product_variant.sku",
        read_only=True,
        allow_null=True
    )
    item_code = serializers.CharField(
        source="item.item_code",
        read_only=True,
        allow_null=True

    )
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

    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ("purchase_order_no","version", "is_current")

    def validate_contact_no(self, value):
        """Validate contact number is 10 digits"""
        if value:  # Only validate if provided (since it's optional)
            if not value.isdigit() or len(value) != 10:
                raise serializers.ValidationError("Contact number must be exactly 10 digits")
        return value

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


class GRNProductSerializer(serializers.ModelSerializer):

    description = serializers.CharField(
        source="purchase_order_product.description", read_only=True
    )
    ordered_quantity = serializers.DecimalField(
        source="purchase_order_product.quantity",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    total_accepted_quantity = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = GRNProduct
        fields = [
            "id",
            "purchase_order_product",
            "description",
            "ordered_quantity",

            # 🔥 NEW
            "total_accepted_quantity",
            "remaining_quantity",

            "received_quantity",
            "rejected_quantity",
        ]

    def get_total_accepted_quantity(self, obj):
        total = GRNProduct.objects.filter(
            purchase_order_product=obj.purchase_order_product
        ).aggregate(
            total=Sum(F("received_quantity") - F("rejected_quantity"))
        )["total"]

        return total or 0


    def get_remaining_quantity(self, obj):
        po_qty = obj.purchase_order_product.quantity

        total_accepted = self.get_total_accepted_quantity(obj)

        return po_qty - total_accepted
    
    
    
    def validate(self, data):
        po_product = data["purchase_order_product"]

        received = data["received_quantity"]
        rejected = data["rejected_quantity"]

        accepted_new = received - rejected

        # exclude current instance (for update)
        queryset = GRNProduct.objects.filter(
            purchase_order_product=po_product
        )

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        # 🔥 calculate TOTAL ACCEPTED (not received)
        total_accepted = queryset.aggregate(
            total=Sum(F("received_quantity") - F("rejected_quantity"))
        )["total"] or 0

        remaining = po_product.quantity - total_accepted

        # 🚨 MAIN FIX
        if accepted_new > remaining:
            raise serializers.ValidationError(
                f"Cannot receive more than remaining qty ({remaining})"
            )

        if rejected > received:
            raise serializers.ValidationError(
                "Rejected qty cannot exceed received qty"
            )

        return data

class GRNSerializer(serializers.ModelSerializer):
    products = GRNProductSerializer(many=True)

    class Meta:
        model = GRN
        fields = [
            "id",
            "purchase_order",
            "grn_date",
            "grn_no",
            "is_completed",
            "products",
        ]
        read_only_fields = ["grn_no", "is_completed"]

    # -------------------------
    # CREATE
    # -------------------------
    def create(self, validated_data):
        products_data = validated_data.pop("products")

        with transaction.atomic():
            grn = GRN.objects.create(**validated_data)

            for product_data in products_data:
                GRNProduct.objects.create(grn=grn, **product_data)

        return grn

    # -------------------------
    # UPDATE
    # -------------------------
    def update(self, instance, validated_data):
        products_data = validated_data.pop("products", None)

        instance.grn_date = validated_data.get("grn_date", instance.grn_date)
        instance.save()

        if products_data is not None:
            instance.products.all().delete()

            for product_data in products_data:
                GRNProduct.objects.create(grn=instance, **product_data)

        return instance

    # -------------------------
    # COMPLETE GRN 🔥
    # -------------------------
    def complete(self, instance):
        complete_grn(instance)
        return instance
    
class InventorySerializer(serializers.ModelSerializer):

    product_variant_name = serializers.CharField(
        source="product_variant.sku", read_only=True
    )
    item_name = serializers.CharField(
        source="item.item_code", read_only=True
    )

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "product_variant",
            "product_variant_name",
            "item",
            "item_name",

            # 🔥 ADD THIS
            "display_name",

            "quantity",
            "uom",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    # 🔥 ADD THIS METHOD
    def get_display_name(self, obj):
        if obj.product_variant:
            return obj.product_variant.sku
        if obj.item:
            return obj.item.item_code
        return None

    def validate(self, data):
        product_variant = data.get("product_variant")
        item_obj = data.get("item")

        if not product_variant and not item_obj:
            raise serializers.ValidationError(
                "Either product_variant or item is required"
            )

        if product_variant and item_obj:
            raise serializers.ValidationError(
                "Only one of product_variant or item allowed"
            )

        return data
    
    


class MaterialIssueItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)

    inventory_item = serializers.PrimaryKeyRelatedField(
        queryset=InventoryItem.objects.all()
    )

    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    uom = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    product_name = serializers.CharField(read_only=True)

    def validate(self, data):
        if data["quantity"] <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return data
    




class MaterialIssueSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)

    issue_number = serializers.CharField()
    issue_type = serializers.ChoiceField(choices=["site", "technician"])

    branch = serializers.PrimaryKeyRelatedField(
        queryset=BranchManagement.objects.all()
    )

    site = serializers.PrimaryKeyRelatedField(
        queryset=SiteManagement.objects.all(),
        required=False,
        allow_null=True
    )

    technician = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False,
        allow_null=True
    )

    issue_date = serializers.DateField()

    items = MaterialIssueItemSerializer(many=True)
    
    
    def validate(self, data):
        issue_type = data.get("issue_type")
        site = data.get("site")
        technician = data.get("technician")

        if issue_type == "technician" and not technician:
            raise serializers.ValidationError("Technician is required")

        if issue_type == "site" and not site:
            raise serializers.ValidationError("Site is required")

        if site and technician:
            raise serializers.ValidationError("Only one destination allowed")

        return data
    

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        user = self.context["request"].user

        with transaction.atomic():
            issue = MaterialIssue.objects.create(
                created_by=user,
                **validated_data   # ✅ now contains objects, not IDs
            )

            for item_data in items_data:
                inventory = item_data["inventory_item"]  # already object
                qty = item_data["quantity"]

                # 🔥 branch validation (VERY IMPORTANT)
                # if inventory.branch != issue.branch:
                #     raise serializers.ValidationError(
                #         f"{inventory} does not belong to this branch"
                #     )

                # 🔥 lock row
                inventory = InventoryItem.objects.select_for_update().get(
                    id=inventory.id
                )

                # 🔥 stock check
                if inventory.quantity < qty:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {inventory}"
                    )

                # 🔥 reduce stock
                InventoryItem.objects.filter(id=inventory.id).update(
                    quantity=F("quantity") - qty
                )

                # 🔥 create item
                MaterialIssueItem.objects.create(
                    material_issue=issue,
                    inventory_item=inventory,
                    quantity=qty,
                    uom=item_data.get("uom")
                )

        return issue
    
    def to_representation(self, instance):
        return {
            "id": instance.id,
            "issue_number": instance.issue_number,
            "issue_type": instance.issue_type,
            "branch": instance.branch.id,
            "site": instance.site.id if instance.site else None,
            "technician": instance.technician.id if instance.technician else None,
            "issue_date": instance.issue_date,
            "items": [
                {
                    "id": item.id,
                    "inventory_item": item.inventory_item.id,
                    "product_name": str(item.inventory_item),
                    "quantity": item.quantity,
                    "uom": item.uom,
                }
                for item in instance.items.all()
            ]
        }   
        
        