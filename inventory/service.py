# services.py
from django.db import transaction
from .models import PurchaseOrder, PurchaseOrderProduct

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
        branch=validated_data.get("branch", old_po.branch),
        book_no=validated_data.get("book_no", old_po.book_no),
        purchase_order_no=old_po.purchase_order_no,  # same PO no across versions
        version=old_po.version + 1,
        is_current=True,
        quotation_ref_no=validated_data.get("quotation_ref_no", old_po.quotation_ref_no),
        quotation_date=validated_data.get("quotation_date", old_po.quotation_date),
        contact_name=validated_data.get("contact_name", old_po.contact_name),
        contact_no=validated_data.get("contact_no", old_po.contact_no),
    )

    # ✅ Set terms_conditions AFTER save
    if terms_conditions is not None:
        new_po.terms_conditions.set(terms_conditions)
    else:
        # if not provided in update, copy from old PO
        new_po.terms_conditions.set(old_po.terms_conditions.all())

    # copy products from request (new version lines)
    for product in products_data:
        PurchaseOrderProduct.objects.create(
            purchase_order=new_po,
            **product
        )

    # calulate the totals and save
    new_po.calculate_totals()

    return new_po