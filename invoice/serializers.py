from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from inventory.models import TermsConditions,TermsConditionType
from .models import (
    Invoice,
    
    CompanyProfile,
    HighSideInvoiceItem,
    LowSideInvoiceItem
)




class HighSideInvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighSideInvoiceItem
        fields = "__all__"
        read_only_fields = ("invoice", "amount")


class LowSideInvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LowSideInvoiceItem
        fields = "__all__"
        read_only_fields = ("invoice", "amount")


# =====================================================
# 🔥 PRO INVOICE SERIALIZER
# =====================================================

class InvoiceSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    high_side_items = HighSideInvoiceItemSerializer(many=True, required=False)
    low_side_items = LowSideInvoiceItemSerializer(many=True, required=False)

    terms_conditions = serializers.PrimaryKeyRelatedField(
        queryset=TermsConditions.objects.all(),
        many=True,
        required=False
    )
    
   

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = (
            "taxable_value",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_tax",
            "grand_total",
            "created_at",
        )

    # =====================================================
    # 🔥 CALCULATION ENGINE
    # =====================================================
    def calculate_totals(self, invoice, high_items, low_items):
    
        taxable_value = Decimal("0")
        gst_total = Decimal("0")
        
    
        invoice.high_side_items.all().delete()
        invoice.low_side_items.all().delete()
        
    
        # ================= HIGH SIDE =================
        for item in high_items:
    
            qty = Decimal(str(item.get("quantity", 0)))
            rate = Decimal(str(item.get("rate", 0)))
            gst_percent = Decimal(str(item.get("gst_percent", 0)))
    
            base = qty * rate
            gst_amount = (base * gst_percent) / Decimal("100")
    
            taxable_value += base
            gst_total += gst_amount
    
            HighSideInvoiceItem.objects.create(
                invoice=invoice,
                product_variant=item.get("product_variant"),
                description=item.get("description"),
                hsn_sac=item.get("hsn_sac"),
                gst_percent=gst_percent,
                quantity=qty,
                unit=item.get("unit"),
                rate=rate
            )
    
            
    
        # ================= LOW SIDE =================
        for item in low_items:
    
            qty = Decimal(str(item.get("quantity", 0)))
            rate = Decimal(str(item.get("rate", 0)))
            gst_percent = Decimal(str(item.get("gst_percent", 0)))
    
            base = qty * rate
            gst_amount = (base * gst_percent) / Decimal("100")
    
            taxable_value += base
            gst_total += gst_amount
    
            LowSideInvoiceItem.objects.create(
                invoice=invoice,
                item=item.get("item"),
                description=item.get("description"),
                gst_percent=gst_percent,
                quantity=qty,
                unit=item.get("unit"),
                rate=rate
            )
    
            
         
    
            # ================= FINAL TOTAL =================
        invoice.taxable_value = taxable_value
        
        # ================= NO GST =================
        if invoice.gst_type == "NO_GST":
        
            invoice.cgst_amount = Decimal("0")
            invoice.sgst_amount = Decimal("0")
            invoice.igst_amount = Decimal("0")
            invoice.total_tax = Decimal("0")
        
            invoice.grand_total = taxable_value
        
        
        # ================= CGST + SGST =================
        elif invoice.gst_type == "CGST_SGST":
        
            invoice.cgst_amount = gst_total / Decimal("2")
            invoice.sgst_amount = gst_total / Decimal("2")
            invoice.igst_amount = Decimal("0")
        
            invoice.total_tax = gst_total
            invoice.grand_total = taxable_value + gst_total
        
        
        # ================= IGST =================
        elif invoice.gst_type == "IGST":
        
            invoice.igst_amount = gst_total
            invoice.cgst_amount = Decimal("0")
            invoice.sgst_amount = Decimal("0")
        
            invoice.total_tax = gst_total
            invoice.grand_total = taxable_value + gst_total        
        invoice.save()    
    # =====================================================
    # CREATE
    # =====================================================
    @transaction.atomic
    def create(self, validated_data):
    
        high_items = validated_data.pop("high_side_items", [])
        low_items = validated_data.pop("low_side_items", [])
        terms = validated_data.pop("terms_conditions", [])
    
        invoice = Invoice.objects.create(**validated_data)
    
        if terms:
            invoice.terms_conditions.set(terms)
    
        self.calculate_totals(invoice, high_items, low_items)
    
        return invoice    

    # =====================================================
    # UPDATE
    # =====================================================
    @transaction.atomic
    def update(self, instance, validated_data):
    
        high_items = validated_data.pop("high_side_items", [])
        low_items = validated_data.pop("low_side_items", [])
        terms = validated_data.pop("terms_conditions", [])
    
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
    
        instance.save()
    
        if terms is not None:
            instance.terms_conditions.set(terms)
    
        self.calculate_totals(instance, high_items, low_items)
    
        return instance


