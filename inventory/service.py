# services.py
from django.db import transaction
from .models import PurchaseOrder, PurchaseOrderProduct

PO_PRODUCT_WRITE_FIELDS = frozenset({
    "product_variant",
    "item",
    "serial_no",
    "sort_order",
    "is_section",
    "section_title",
    "description",
    "quantity",
    "uom",
    "rate",
    "hsn_sac",
})


def sanitize_po_product_line(product):
    data = dict(product)
    return {k: v for k, v in data.items() if k in PO_PRODUCT_WRITE_FIELDS}


@transaction.atomic
def create_new_po_version(old_po, validated_data, products_data):
    # 🔒 Never let M2M go into create()
    validated_data = validated_data.copy()
    terms_conditions = validated_data.pop("terms_conditions", None)

    # mark old PO as not current
    old_po.is_current = False
    old_po.save(update_fields=["is_current"])

    # create new PO version (ONLY normal fields + FKs)
    new_po = PurchaseOrder.objects.create(
        vendor=validated_data.get("vendor", old_po.vendor),
        site=validated_data.get("site", old_po.site),
        delivery_destination=validated_data.get("delivery_destination", old_po.delivery_destination),
        branch=validated_data.get("branch", old_po.branch),
        book_no=validated_data.get("book_no", old_po.book_no),
        purchase_order_no=old_po.purchase_order_no,  # same PO no across versions
        version=old_po.version + 1,
        is_current=True,

        po_date=validated_data.get("po_date", old_po.po_date),
        gst_percentage=validated_data.get("gst_percentage", old_po.gst_percentage),
        gst_type=validated_data.get("gst_type", old_po.gst_type),
        transport_charges=validated_data.get("transport_charges", old_po.transport_charges),
        round_off=validated_data.get("round_off", old_po.round_off),
        quotation_ref_no=validated_data.get("quotation_ref_no", old_po.quotation_ref_no),
        quotation_date=validated_data.get("quotation_date", old_po.quotation_date),
        contact_name=validated_data.get("contact_name", old_po.contact_name),
        contact_no=validated_data.get("contact_no", old_po.contact_no),
        note =validated_data.get("note", old_po.note)
    )

    # ✅ Set terms_conditions AFTER save
    if terms_conditions is not None:
        new_po.terms_conditions.set(terms_conditions)
    else:
        # if not provided in update, copy from old PO
        new_po.terms_conditions.set(old_po.terms_conditions.all())

    # copy products from request (new version lines)
    section_counter = 0
    child_counter = 0
    for idx, product in enumerate(products_data):
        product = product.copy() if hasattr(product, 'copy') else product
        product['sort_order'] = idx + 1
        if product.get('is_section', False):
            section_counter += 1
            child_counter = 0
            product['serial_no'] = str(section_counter)
        else:
            if section_counter > 0:
                child_counter += 1
                product['serial_no'] = f"{section_counter}.{child_counter}"
            else:
                child_counter += 1
                product['serial_no'] = str(child_counter)

        PurchaseOrderProduct.objects.create(
            purchase_order=new_po,
            **sanitize_po_product_line(product)
        )

    # calulate the totals and save
    new_po.calculate_totals()

    return new_po