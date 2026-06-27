from rest_framework import serializers
from .models import *
from .service import create_new_po_version
from django.db import transaction
from django.db.models import Sum, F
import uuid

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
    
    # Add read-only fields for display
    purchase_order_no = serializers.CharField(
        source='purchase_order.purchase_order_no',
        read_only=True
    )
    vendor_name = serializers.CharField(
        source='purchase_order.vendor.name',
        read_only=True
    )
    po_date = serializers.DateField(
        source='purchase_order.po_date',
        read_only=True
    )

    class Meta:
        model = GRN
        fields = [
            "id",
            "purchase_order",
            "purchase_order_no",
            "vendor_name",
            "po_date",
            "grn_date",
            "grn_no",
            "is_completed",
            "products",
        ]
        read_only_fields = ["grn_no", "is_completed", "purchase_order_no", "vendor_name", "po_date"]

    # -------------------------
    # CREATE (AUTO-COMPLETE)
    # -------------------------
    def create(self, validated_data):
        products_data = validated_data.pop("products")

        with transaction.atomic():
            # Create GRN
            grn = GRN.objects.create(**validated_data)

            # Create GRN products
            for product_data in products_data:
                GRNProduct.objects.create(grn=grn, **product_data)

            # Refresh to get all products
            grn.refresh_from_db()

            # 🔥 AUTO-COMPLETE: Update inventory immediately
            update_inventory_from_grn(grn)

            # 🔥 AUTO-COMPLETE: Mark as completed
            grn.is_completed = True
            grn.save(update_fields=["is_completed"])

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
            "total_in_quantity",
            "total_out_quantity",
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

    product_name = serializers.SerializerMethodField()
    item_code = serializers.SerializerMethodField()
    
    def get_product_name(self, obj):
        """Get product name from inventory item"""
        if obj.inventory_item:
            # Try different name fields
            if hasattr(obj.inventory_item, 'item') and obj.inventory_item.item:
                return obj.inventory_item.item.material_type_name or obj.inventory_item.item.item_code
            elif hasattr(obj.inventory_item, 'product_variant') and obj.inventory_item.product_variant:
                return obj.inventory_item.product_variant.product_model.model_no
        return "Unknown"
    
    def get_item_code(self, obj):
        """Get item code from inventory item"""
        if obj.inventory_item:
            if hasattr(obj.inventory_item, 'item') and obj.inventory_item.item:
                return obj.inventory_item.item.item_code
            elif hasattr(obj.inventory_item, 'product_variant') and obj.inventory_item.product_variant:
                return obj.inventory_item.product_variant.sku
        return "Unknown"

    def validate(self, data):
        if data["quantity"] <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return data
    




class MaterialIssueSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)

    issue_number = serializers.CharField(read_only=True)
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

            # ✅ Generate issue number
            last_issue = MaterialIssue.objects.order_by("-id").first()
            if last_issue:
                last_id = last_issue.id + 1
            else:
                last_id = 1

            issue_number = f"ISS-{uuid.uuid4().hex[:6].upper()}"

            issue = MaterialIssue.objects.create(
                issue_number=issue_number,   # 🔥 added
                created_by=user,
                **validated_data
            )

            for item_data in items_data:
                inventory = item_data["inventory_item"]
                qty = item_data["quantity"]

                inventory = InventoryItem.objects.select_for_update().get(
                    id=inventory.id
                )

                if inventory.quantity < qty:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {inventory}"
                    )

                InventoryItem.objects.filter(id=inventory.id).update(
                    quantity=F("quantity") - qty,
                    total_out_quantity=F("total_out_quantity") + qty
                )

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
            "branch_name": instance.branch.name if instance.branch else None,
            "site": instance.site.id if instance.site else None,
            "site_name": instance.site.name if instance.site else None,
            "technician": instance.technician.id if instance.technician else None,
            "technician_name": f"{instance.technician.first_name} {instance.technician.last_name}" if instance.technician else None,
            "issue_date": instance.issue_date,
            "items": [
                {
                    "id": item.id,
                    "inventory_item": item.inventory_item.id,
                    "inventory_item_name": str(item.inventory_item),
                    "display_name": str(item.inventory_item),
                    "quantity": item.quantity,
                    "uom": item.uom,
                }
                for item in instance.items.all()
            ]
        }   
        
        


class MaterialReturnItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialReturnItem
        fields = [
            "id",
            "material_issue_item",
            "quantity",
        ]

    def validate(self, data):
        issue_item = data["material_issue_item"]
        qty = data["quantity"]

        if qty <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")

        # 🔥 Already returned qty
        already_returned = MaterialReturnItem.objects.filter(
            material_issue_item=issue_item
        ).aggregate(total=Sum("quantity"))["total"] or 0

        if already_returned + qty > issue_item.quantity:
            raise serializers.ValidationError(
                f"Return exceeds issued qty. Issued={issue_item.quantity}, Returned={already_returned}"
            )

        return data
 

class MaterialReturnSerializer(serializers.ModelSerializer):
    items = MaterialReturnItemSerializer(many=True)
    issue_number = serializers.CharField(source='material_issue.issue_number', read_only=True)

    class Meta:
        model = MaterialReturn
        fields = [
            "id",
            "material_issue",
            "issue_number",
            "return_number",
            "return_date",
            "created_by",
            "is_completed",
            "items"
        ]
        read_only_fields = ["return_number", "created_by", "issue_number", "is_completed"]

    def validate(self, data):
        issue = data["material_issue"]
        items = data.get("items", [])

        if not items:
            raise serializers.ValidationError("At least one item is required")

        for item in items:
            if item["material_issue_item"].material_issue != issue:
                raise serializers.ValidationError(
                    "All items must belong to selected Material Issue"
                )

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        items_data = validated_data.pop("items")

        with transaction.atomic():
            # ✅ create return
            material_return = MaterialReturn.objects.create(
                **validated_data,
                # created_by=request.user
            )

            # 🔥 Lock issue items (important for concurrency)
            issue_item_ids = [item["material_issue_item"].id for item in items_data]

            issue_items_map = {
                i.id: i for i in MaterialIssueItem.objects.select_for_update().filter(id__in=issue_item_ids)
            }

            return_items = []
            for item in items_data:
                issue_item = issue_items_map[item["material_issue_item"].id]

                # 🔥 Re-check quantity inside transaction
                already_returned = MaterialReturnItem.objects.filter(
                    material_issue_item=issue_item
                ).aggregate(total=Sum("quantity"))["total"] or 0

                if already_returned + item["quantity"] > issue_item.quantity:
                    raise serializers.ValidationError(
                        f"Return exceeds issued qty for item {issue_item.id}"
                    )

                return_items.append(
                    MaterialReturnItem(
                        material_return=material_return,
                        material_issue_item=issue_item,
                        quantity=item["quantity"]
                    )
                )

            MaterialReturnItem.objects.bulk_create(return_items)

        return material_return 
    

class DeliveryChallanItemSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(
        source="material_issue_item.inventory_item",
        read_only=True
    )
    issued_quantity = serializers.DecimalField(
        source="material_issue_item.quantity",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = DeliveryChallanItem
        fields = (
            "id",
            "material_issue_item",
            "inventory_item_name",
            "issued_quantity",
            "quantity",
        )

    def validate(self, data):
        issue_item = data["material_issue_item"]
        issued_qty = issue_item.quantity

        dispatched_qty = DeliveryChallanItem.objects.filter(
            material_issue_item=issue_item
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        remaining = issued_qty - dispatched_qty

        if data["quantity"] > remaining:
            raise serializers.ValidationError(
                f"Only {remaining} quantity remaining"
            )

        return data

class DeliveryChallanSerializer(serializers.ModelSerializer):
    items = DeliveryChallanItemSerializer(many=True)
    issue_number = serializers.CharField(
        source="material_issue.issue_number",
        read_only=True
    )

    class Meta:
        model = DeliveryChallan
        fields = "__all__"
        read_only_fields = (
            "dc_number",
            "created_by",
            "issue_number",
        )

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        
        dc = DeliveryChallan.objects.create(
            **validated_data,
            created_by=self.context["request"].user
        )

        for item_data in items_data:
            DeliveryChallanItem.objects.create(
                delivery_challan=dc,
                **item_data
            )

        return dc

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["issue_number"] = (
            instance.material_issue.issue_number
            if instance.material_issue
            else None
        )
        return data