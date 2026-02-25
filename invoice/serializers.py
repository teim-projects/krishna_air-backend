from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from .models import Invoice, InvoiceItem, InvoiceTaxBreakup, CompanyProfile


class InvoiceItemSerializer(serializers.ModelSerializer):

    variant_sku = serializers.CharField(
        source="product_variant.sku",
        read_only=True
    )

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

    item_code = serializers.CharField(
        source="item.item_code",
        read_only=True
    )

    class Meta:
        model = InvoiceItem
        fields = "__all__"
        read_only_fields = ("invoice", "amount")

class InvoiceTaxBreakupSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTaxBreakup
        fields = "__all__"
        read_only_fields = ("invoice",)


# =====================================================
# 🔥 PRO INVOICE SERIALIZER
# =====================================================

class InvoiceSerializer(serializers.ModelSerializer):

    items = InvoiceItemSerializer(many=True)
    tax_breakups = InvoiceTaxBreakupSerializer(many=True, required=False)

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
    def calculate_totals(self, invoice, items_data):

        taxable_value = Decimal("0")
        gst_total = Decimal("0")

        invoice.items.all().delete()
        invoice.tax_breakups.all().delete()

        items_bulk = []
        tax_map = {}

        for item in items_data:

            qty = Decimal(str(item.get("quantity", 0)))
            rate = Decimal(str(item.get("rate", 0)))
            gst_percent = Decimal(str(item.get("gst_percent", 0)))

            base_amount = qty * rate
            gst_amount = (base_amount * gst_percent) / Decimal("100")

            taxable_value += base_amount
            gst_total += gst_amount

            items_bulk.append(
                InvoiceItem(
                    invoice=invoice,
                    product_variant=item.get("product_variant"),
                    item=item.get("item"),
                    description=item.get("description", ""),
                    hsn_sac=item.get("hsn_sac"),
                    gst_percent=gst_percent,
                    quantity=qty,
                    unit=item.get("unit", "NOS"),
                    rate=rate,
                    amount=base_amount
                )
            )

            tax_map.setdefault(gst_percent, Decimal("0"))
            tax_map[gst_percent] += base_amount

        InvoiceItem.objects.bulk_create(items_bulk)

        tax_bulk = []

        for gst_percent, value in tax_map.items():

            if invoice.gst_type == "CGST_SGST":

                half = gst_percent / Decimal("2")

                tax_bulk.append(
                    InvoiceTaxBreakup(
                        invoice=invoice,
                        taxable_value=value,
                        cgst_rate=half,
                        cgst_amount=(value * half) / Decimal("100"),
                        sgst_rate=half,
                        sgst_amount=(value * half) / Decimal("100"),
                    )
                )
            else:
                tax_bulk.append(
                    InvoiceTaxBreakup(
                        invoice=invoice,
                        taxable_value=value,
                        igst_rate=gst_percent,
                        igst_amount=(value * gst_percent) / Decimal("100"),
                    )
                )

        InvoiceTaxBreakup.objects.bulk_create(tax_bulk)

        invoice.taxable_value = taxable_value
        invoice.total_tax = gst_total

        if invoice.gst_type == "CGST_SGST":
            invoice.cgst_amount = gst_total / Decimal("2")
            invoice.sgst_amount = gst_total / Decimal("2")
            invoice.igst_amount = Decimal("0")
        else:
            invoice.igst_amount = gst_total
            invoice.cgst_amount = Decimal("0")
            invoice.sgst_amount = Decimal("0")

        invoice.grand_total = taxable_value + gst_total
        invoice.save()

    # =====================================================
    # CREATE
    # =====================================================
    @transaction.atomic
    def create(self, validated_data):

        items_data = validated_data.pop("items", [])

        invoice = Invoice.objects.create(**validated_data)

        self.calculate_totals(invoice, items_data)

        return invoice

    # =====================================================
    # UPDATE
    # =====================================================
    @transaction.atomic
    def update(self, instance, validated_data):

        items_data = validated_data.pop("items", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        self.calculate_totals(instance, items_data)

        return instance
