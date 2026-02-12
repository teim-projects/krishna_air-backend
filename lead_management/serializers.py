from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Customer, lead_management ,  LeadFollowUp, LeadFAQ, LeadFollowUpFAQAnswer , lead_product
from api.serializers import CustomUserDetailsSerializer
from django.contrib.auth import get_user_model
from django.db import transaction
from product_management.models import *

User = get_user_model()

class CustomerSerializer(serializers.ModelSerializer):
   class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ('id',)

class LeadFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadFAQ
        fields = ["id", "question", "is_active", "sort_order"]


class LeadFollowUpFAQAnswerSerializer(serializers.ModelSerializer):
    # Extra read-only field to send question text directly
    faq_question = serializers.CharField(source="faq.question", read_only=True)
    
    class Meta:
        model = LeadFollowUpFAQAnswer
        fields = ["id", "faq", "faq_question", "answer"]
        read_only_fields = ["id", "faq_question"]



class LeadProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    ac_type = serializers.PrimaryKeyRelatedField(
        queryset=acType.objects.all(), required=False
    )

    ac_sub_type = serializers.PrimaryKeyRelatedField(
        queryset=acSubTypes.objects.all(), required=False
    )

    brand = serializers.PrimaryKeyRelatedField(
        queryset=brand.objects.all(), required=False
    )

    product_model = serializers.PrimaryKeyRelatedField(
        queryset=ProductModel.objects.all(), required=False
    )

    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(), required=False
    )

    class Meta:
        model = lead_product
        fields = [
            'id',
            'ac_type',
            'ac_sub_type',
            'brand',
            'product_model',
            'variant',
            'quantity',
            'expected_price',
            'remarks'
        ]


class LeadProductReadSerializer(serializers.ModelSerializer):
    ac_type = serializers.StringRelatedField()
    ac_sub_type = serializers.StringRelatedField()
    brand = serializers.StringRelatedField()
    product_model = serializers.StringRelatedField()
    variant = serializers.StringRelatedField()

    class Meta:
        model = lead_product
        fields = [
            'id',
            'ac_type',
            'ac_sub_type',
            'brand',
            'product_model',
            'variant',
            'quantity',
            'expected_price',
            'remarks'
        ]

class LeadFollowUpSerializer(serializers.ModelSerializer):
    """
    Main serializer for LeadFollowUp with nested FAQ answers.
    """

    faq_answers = LeadFollowUpFAQAnswerSerializer(
        many=True, required=False
    )

    products = LeadProductSerializer(
        many=True,
        required=False,
        write_only=True
    )

    product_details = LeadProductReadSerializer(
        many=True,
        source="lead.lead_products",
        read_only=True
    )

    lead_customer_name = serializers.CharField(
        source="lead.customer.name",
        read_only=True
    )

    class Meta:
        model = LeadFollowUp
        fields = [
            "id",
            "lead",
            "lead_customer_name",
            "followup_date",
            "next_followup_date",
            "remarks",
            "status",
            "created_by",
            "created_at",
            "faq_answers",
            "products",
            "product_details",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    # =========================
    # CREATE
    # =========================
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        
        faq_data = validated_data.pop("faq_answers", [])
        products_data = validated_data.pop("products", [])

        deleted_ids = request.data.get("deleted_products", [])
        
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user

        followup = LeadFollowUp.objects.create(**validated_data)

        for item in faq_data:
            LeadFollowUpFAQAnswer.objects.create(
                followup=followup,
                **item
            )

        if deleted_ids:
            lead_product.objects.filter(
                lead=followup.lead,
                id__in=deleted_ids
            ).delete()

        self._sync_products(followup.lead, products_data)

        return followup

    # =========================
    # UPDATE
    # =========================
    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")

        faq_data = validated_data.pop("faq_answers", None)
        products_data = validated_data.pop("products", None)
        deleted_ids = request.data.get("deleted_products", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if faq_data is not None:
            instance.faq_answers.all().delete()
            for item in faq_data:
                LeadFollowUpFAQAnswer.objects.create(
                    followup=instance,
                    **item
                )
        
        # 🔥 DELETE PRODUCTS
        if deleted_ids:
            lead_product.objects.filter(
                lead=instance.lead,
                id__in=deleted_ids
            ).delete()

        if products_data is not None:
            self._sync_products(instance.lead, products_data)

        return instance

    # =========================
    # PRODUCT SYNC (CORE LOGIC)
    # =========================
    def _sync_products(self, lead, products_data):
        """
        Update existing lead products and create new ones if id is not provided.
        """
        for product in products_data:
            print("product", product)
            product_id = product.get("id")

            # =====================
            # UPDATE EXISTING
            # =====================
            if product_id:
                lead_product.objects.filter(
                    id=product_id,
                    lead=lead
                ).update(
                    quantity=product.get("quantity"),
                    expected_price=product.get("expected_price"),
                    remarks=product.get("remarks", "")
                )
                continue

            # =====================
            # CREATE NEW
            # =====================
            required_fields = [
                "ac_type",
                "ac_sub_type",
                "brand",
                "product_model",
                "variant",
            ]

            if all(product.get(field) for field in required_fields):
                lead_product.objects.create(
                    lead=lead,
                    ac_type=product["ac_type"],
                    ac_sub_type=product["ac_sub_type"],
                    brand=product["brand"],
                    product_model=product["product_model"],
                    variant=product["variant"],
                    quantity=product.get("quantity"),
                    expected_price=product.get("expected_price"),
                    remarks=product.get("remarks", "")
                )

            # ❌ silently ignore incomplete rows

# class LeadProductSerializer(serializers.ModelSerializer):
#     id = serializers.IntegerField(required=False)
#     class Meta:
#         model = lead_product
#         fields = [
#             'id',
#             'ac_type',
#             'ac_sub_type',
#             'brand',
#             'product_model',
#             'variant',
#             'quantity',
#             'expected_price',
#             'remarks'
#         ]


# class LeadProductReadSerializer(serializers.ModelSerializer):
#     ac_type = serializers.StringRelatedField()
#     ac_sub_type = serializers.StringRelatedField()
#     brand = serializers.StringRelatedField()
#     product_model = serializers.StringRelatedField()
#     variant = serializers.StringRelatedField()

#     class Meta:
#         model = lead_product
#         fields = [
#             'id',
#             'ac_type',
#             'ac_sub_type',
#             'brand',
#             'product_model',
#             'variant',
#             'quantity',
#             'expected_price',
#             'remarks'
#         ]



class LeadSerializer(serializers.ModelSerializer):
    
    FIXED_SOURCES = [
        'google_ads',
        'indiamart',
        'bni',
        'justdial',
        'reference',
        'architect/interior_designe',
        'builder',
        'existing_customer',
        'ka_staff',
        'other',
    ]
    products = LeadProductSerializer(many=True, write_only=True,  required=False)
    product_details = LeadProductReadSerializer(
        many=True,
        source="lead_products",
        read_only=True
    )
    # Customer fields
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_contact = serializers.CharField(source="customer.contact_number", read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_secondary_email = serializers.EmailField(source="customer.secondary_email", read_only=True)
    customer_address = serializers.CharField(source="customer.address", read_only=True)
    assign_to_details = CustomUserDetailsSerializer(source="assign_to", read_only=True)
    creatd_by_details = CustomUserDetailsSerializer(source="creatd_by", read_only=True)
    referance_by_details = CustomUserDetailsSerializer(source="referance_by", read_only=True)
    followups = LeadFollowUpSerializer(many=True, read_only=True)

    class Meta:
        model = lead_management
        fields = [
            "id",
            "requirements_details",
            "lead_source",
            "lead_source_input",
            "status",
            "lead_type",
            "is_service_lead",
            "project_name",
            "project_adderess",
            "date",
            "enquiry_date",
            "followup_date",
            "remarks",
            "customer",        
            "customer_name",
            "customer_contact",
            "customer_email",
            "customer_address",
            "customer_secondary_email",
            "assign_to",        
            "creatd_by",
            'referance_by', 
            "assign_to_details",
            "creatd_by_details",
            "referance_by_details",
            "followups",
            "products",
            "product_details",   
             
         
        ]
        read_only_fields = ("id","creatd_by","date") 


       

        # def validate_lead_source(self, value):
        #     value = value.strip()

        #     # allow fixed sources
        #     if value in self.FIXED_SOURCES:
        #         return value

    @transaction.atomic
    def create(self, validated_data):
        products = validated_data.pop("products", [])
        lead = lead_management.objects.create(**validated_data)
        for product in products:
            lead_product.objects.create(
                lead=lead,
                **product
            )
        return lead
    
    @transaction.atomic
    def update(self, instance, validated_data):
        products = validated_data.pop("products", [])
        # print("VALIDATED PRODUCTS:", products)
        deleted_ids = self.context["request"].data.get("deleted_products", [])
    
        # 1️⃣ Update lead fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
    
        # 2️⃣ Delete removed products
        if deleted_ids:
            lead_product.objects.filter(
                lead=instance,
                id__in=deleted_ids
            ).delete()
    
        # 3️⃣ Update / Create products safely
        for product in products:
            product_id = product.get("id")
    
            # ✅ UPDATE EXISTING PRODUCT
            if product_id:
                lead_product.objects.filter(
                    id=product_id,
                    lead=instance
                ).update(
                    quantity=product.get("quantity"),
                    expected_price=product.get("expected_price"),
                    remarks=product.get("remarks", "")
                )
                continue
            
            # ✅ CREATE ONLY IF ALL REQUIRED FKs PRESENT
            required_fk_fields = [
                "ac_type",
                "ac_sub_type",
                "brand",
                "product_model",
                "variant",
            ]
    
            if all(product.get(field) for field in required_fk_fields):
                lead_product.objects.create(
                    lead=instance,
                    **product
                )
            # else: silently ignore incomplete rows
    
        return instance


    def validate_lead_source(self, value):
        value = value.strip().lower()
    
        if value in self.FIXED_SOURCES:
            return value
    
        # allow custom value only if "other"
        if value and value not in self.FIXED_SOURCES:
            return value
    
        raise serializers.ValidationError("Invalid lead source")



