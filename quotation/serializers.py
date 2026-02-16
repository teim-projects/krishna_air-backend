from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Quotation, QuotationVersion,QuotationHighSideItem
from django.db import transaction


class QuotationHighSideItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuotationHighSideItem
        fields = "__all__"
        read_only_fields = ("quotation_version", "total_price")



class QuotationVersionSerializer(serializers.ModelSerializer):

    high_side_items = QuotationHighSideItemSerializer(many=True)

    class Meta:
        model = QuotationVersion
        fields = "__all__"
       
        read_only_fields = (
            "quotation",      # ⭐ ADD THIS
            "version_no",
            "is_active",
            "created_by",
        )



class QuotationSerializer(serializers.ModelSerializer):

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_contact = serializers.CharField(source="customer.contact_number", read_only=True)
    

    versions = QuotationVersionSerializer(many=True)


    class Meta:
        model = Quotation
        fields = "__all__"

    # ============================
    # CREATE
    # ============================
    @transaction.atomic
    def create(self, validated_data):
    
        request = self.context.get("request")
    
        versions_data = validated_data.pop("versions")
    
        quotation = Quotation.objects.create(**validated_data)
    
        version_data = versions_data[0]
        items = version_data.pop("high_side_items")
    
        subtotal = 0
        total_gst = 0
    
        version = QuotationVersion.objects.create(
            quotation=quotation,
            version_no=1,
            is_active=True,
            created_by=request.user if request else None,
            **version_data
        )
    
        for item in items:
    
            qty = item["quantity"]
            price = item["unit_price"]
            gst_percent = item.get("gst_percent", 0)
    
            total_price = qty * price
            gst_value = (total_price * gst_percent) / 100
    
            subtotal += total_price
            total_gst += gst_value
    
            QuotationHighSideItem.objects.create(
                quotation_version=version,
                total_price=total_price,
                **item
            )
    
        # Decide GST split
        cgst_total = 0
        sgst_total = 0
        igst_total = 0
        
        if version.gst_type == "CGST_SGST":
            cgst_total = total_gst / 2
            sgst_total = total_gst / 2
        else:
            igst_total = total_gst
        
        version.subtotal = subtotal
        version.gst_amount = total_gst
        version.cgst_amount = cgst_total
        version.sgst_amount = sgst_total
        version.igst_amount = igst_total
        
        version.total_amount = (
            subtotal
            + total_gst
            + version.mathadi_charges
            + version.transportation_charges
        )
        version.save()
        
            
        return quotation

    # ============================
    # UPDATE (NEW VERSION CREATE)
    # ============================
    @transaction.atomic
    def update(self, instance, validated_data):
    
        request = self.context.get("request")
    
        versions_data = validated_data.pop("versions")
    
        old_version = instance.versions.filter(is_active=True).first()
        old_version.is_active = False
        old_version.save()
    
        new_version_no = old_version.version_no + 1
    
        version_data = versions_data[0]
        items = version_data.pop("high_side_items")
    
        subtotal = 0
        total_gst = 0
    
        new_version = QuotationVersion.objects.create(
            quotation=instance,
            version_no=new_version_no,
            is_active=True,
            created_by=request.user if request else None,
            **version_data
        )
    
        for item in items:
    
            qty = item["quantity"]
            price = item["unit_price"]
            gst_percent = item.get("gst_percent", 0)
    
            total_price = qty * price
            gst_value = (total_price * gst_percent) / 100
    
            subtotal += total_price
            total_gst += gst_value
    
            QuotationHighSideItem.objects.create(
                quotation_version=new_version,
                total_price=total_price,
                **item
            )
    
        # Decide GST split
        cgst_total = 0
        sgst_total = 0
        igst_total = 0
        
        if new_version.gst_type == "CGST_SGST":
            cgst_total = total_gst / 2
            sgst_total = total_gst / 2
        else:
            igst_total = total_gst
        
        new_version.subtotal = subtotal
        new_version.gst_amount = total_gst
        new_version.cgst_amount = cgst_total
        new_version.sgst_amount = sgst_total
        new_version.igst_amount = igst_total
        
        new_version.total_amount = (
            subtotal
            + total_gst
            + new_version.mathadi_charges
            + new_version.transportation_charges
        )
        new_version.save()

    
        return instance
    