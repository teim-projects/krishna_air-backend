from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Customer, lead_management ,  LeadFollowUp, LeadFAQ, LeadFollowUpFAQAnswer , lead_product
from api.serializers import CustomUserDetailsSerializer
from django.contrib.auth import get_user_model
from django.db import transaction

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


class LeadFollowUpSerializer(serializers.ModelSerializer):
    """
    Main serializer for LeadFollowUp with nested FAQ answers.
    """
    # nested answers
    faq_answers = LeadFollowUpFAQAnswerSerializer(many=True, required=False, read_only=False)

    # you can also expose some lead info if you want
    lead_customer_name = serializers.CharField(source="lead.customer.name", read_only=True)

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
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def create(self, validated_data):
        faq_data = validated_data.pop("faq_answers", [])
        request = self.context.get("request")

        # set created_by from logged in user
        if request and request.user and request.user.is_authenticated:
            validated_data["created_by"] = request.user

        followup = LeadFollowUp.objects.create(**validated_data)

        # create FAQ answers
        for item in faq_data:
            LeadFollowUpFAQAnswer.objects.create(
                followup=followup,
                **item
            )

        return followup

    def update(self, instance, validated_data):
        faq_data = validated_data.pop("faq_answers", None)

        # update simple fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # if faq_answers sent, replace existing ones (simple & safe)
        if faq_data is not None:
            instance.faq_answers.all().delete()
            for item in faq_data:
                LeadFollowUpFAQAnswer.objects.create(
                    followup=instance,
                    **item
                )

        return instance
    


class LeadProductSerializer(serializers.ModelSerializer):

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
    products = LeadProductSerializer(many=True, write_only=True)
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
        deleted_ids = self.context["request"].data.get("deleted_products", [])
    
        # ✅ 1. Update lead fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
    
        # ✅ 2. Delete removed products
        if deleted_ids:
            lead_product.objects.filter(
                lead=instance,
                id__in=deleted_ids
            ).delete()
    
        # ✅ 3. Add new products
        for product in products:
            lead_product.objects.create(
                lead=instance,
                **product
            )
    
        return instance
    



    def validate_lead_source(self, value):
        value = value.strip().lower()
    
        if value in self.FIXED_SOURCES:
            return value
    
        # allow custom value only if "other"
        if value and value not in self.FIXED_SOURCES:
            return value
    
        raise serializers.ValidationError("Invalid lead source")



