from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Customer, lead_management ,  LeadFollowUp, LeadFAQ, LeadFollowUpFAQAnswer
from api.serializers import CustomUserDetailsSerializer
from django.contrib.auth import get_user_model

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
    



class LeadSerializer(serializers.ModelSerializer):

    
    FIXED_SOURCES = [
        'google_ads',
        'indiamart',
        'bni',
        'other',
    ]
    # Customer fields
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_contact = serializers.CharField(source="customer.contact_number", read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_secondary_email = serializers.EmailField(source="customer.secondary_email", read_only=True)

    assign_to_details = CustomUserDetailsSerializer(source="assign_to", read_only=True)
    creatd_by_details = CustomUserDetailsSerializer(source="creatd_by", read_only=True)
    referance_by_details = CustomUserDetailsSerializer(source="referance_by", read_only=True)
    followups = LeadFollowUpSerializer(many=True, read_only=True)
    class Meta:
        model = lead_management
        fields = [
            "id",
            "requirements_details",
            "hvac_application",
            "capacity_required",
            "lead_source",
            "status",
            "project_name",
            "project_adderess",
            "date",
            "followup_date",
            "remarks",
            "customer",        
            "customer_name",
            "customer_contact",
            "customer_email",
            "customer_secondary_email",
            "assign_to",        
            "creatd_by",
            'referance_by', 
            "assign_to_details",
            "creatd_by_details",
            "referance_by_details",
            "followups",    
         
        ]
        read_only_fields = ("id",) 


        def validate_lead_source(self, value):
            value = value.strip()

            # allow fixed sources
            if value in self.FIXED_SOURCES:
                return value
            
    


