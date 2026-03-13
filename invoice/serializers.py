from rest_framework import serializers
from django.db import transaction
from num2words import num2words
from decimal import Decimal
from inventory.models import TermsConditions,TermsConditionType
from .models import (
    Invoice,
    
    CompanyProfile,
    HighSideInvoiceItem,
    LowSideInvoiceItem
)




class HighSideInvoiceItemSerializer(serializers.ModelSerializer):

    ac_type_name = serializers.CharField(
        source="product_variant.product_model.ac_sub_type_id.ac_type_id.name",
        read_only=True
    )

    ac_sub_type_name = serializers.CharField(
        source="product_variant.product_model.ac_sub_type_id.name",
        read_only=True
    )

    brand_name = serializers.CharField(
        source="product_variant.product_model.brand_id.name",
        read_only=True
    )

    model_no = serializers.CharField(
        source="product_variant.product_model.model_no",
        read_only=True
    )

    variant_sku = serializers.CharField(
        source="product_variant.sku",
        read_only=True
    )

    class Meta:
        model = HighSideInvoiceItem
        fields = "__all__"
        read_only_fields = ("invoice", "amount")

class LowSideInvoiceItemSerializer(serializers.ModelSerializer):

    item_code = serializers.CharField(
        source="item.item_code",
        read_only=True
    )

    material_type_name = serializers.CharField(
        source="item.material_type_id.name",
        read_only=True
    )

    item_type_name = serializers.CharField(
        source="item.item_type_id.name",
        read_only=True
    )

    feature_type_name = serializers.CharField(
        source="item.feature_type_id.name",
        read_only=True
    )

    item_class_name = serializers.CharField(
        source="item.item_class_id.name",
        read_only=True
    )

    class Meta:
        model = LowSideInvoiceItem
        fields = "__all__"
        read_only_fields = ("invoice", "amount")
# =====================================================
# 🔥 PRO INVOICE SERIALIZER
# =====================================================

class InvoiceSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    terms_conditions_details = serializers.SerializerMethodField()
    
    high_side_items = HighSideInvoiceItemSerializer(many=True, required=False)
    low_side_items = LowSideInvoiceItemSerializer(many=True, required=False)
    site_name = serializers.CharField(source="site.site_name", read_only=True)

    terms_conditions = serializers.PrimaryKeyRelatedField(
        queryset=TermsConditions.objects.all(),
        many=True,
        required=False
    )
    customer_phone = serializers.CharField(
    source="customer.contact_number",
    read_only=True
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

    def get_terms_conditions_details(self, obj):
    
        data = []
    
        for term in obj.terms_conditions.all():
    
            data.append({
                "id": term.id,
                "terms": term.terms,
                "terms_condition_type_name": term.terms_condition_type.name
            })
    
        return data        

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

        
        # ================= AMOUNT IN WORDS =================
        rupees = int(invoice.grand_total)
        paise = int((invoice.grand_total - rupees) * 100)
        
        words = num2words(rupees, lang="en_IN").title()
        
        if paise > 0:
            paise_words = num2words(paise, lang="en_IN").title()
            invoice.amount_in_words = f"{words} Rupees and {paise_words} Paise Only"
        else:
            invoice.amount_in_words = f"{words} Rupees Only"                 
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


