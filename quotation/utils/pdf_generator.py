# quotation/utils/pdf_generator.py
from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _item_line_amount(item):
    """Return line total including GST and extra charges where stored on the model."""
    total = getattr(item, 'total_with_gst', None)
    if total is not None and total > 0:
        return Decimal(total)

    qty = Decimal(getattr(item, 'quantity', 0) or 0)
    rate = Decimal(getattr(item, 'unit_price', 0) or 0)
    base = qty * rate
    gst = Decimal(getattr(item, 'gst_amount', 0) or 0)
    mathadi = Decimal(getattr(item, 'mathadi_charges', 0) or 0)
    transport = Decimal(getattr(item, 'transportation_charges', 0) or 0)
    return base + gst + mathadi + transport


def _item_base_amount(item):
    base = getattr(item, 'base_amount', None)
    if base is not None and base > 0:
        return Decimal(base)
    qty = Decimal(getattr(item, 'quantity', 0) or 0)
    rate = Decimal(getattr(item, 'unit_price', 0) or 0)
    return qty * rate


def _build_quotation_pdf_context(quotation, version):
    high_side_items = list(
        version.high_side_items.select_related('product_variant__product_model').all()
    )
    low_side_items = list(
        version.low_side_items.select_related(
            'item__material_type_id',
            'item__item_type_id',
            'item__feature_type_id',
            'item__brand',
        ).all()
    )
    service_items = list(version.service_items.select_related('service').all())

    high_side_total = sum((_item_line_amount(i) for i in high_side_items), Decimal('0'))
    low_side_total = sum((_item_line_amount(i) for i in low_side_items), Decimal('0'))
    service_total = sum((_item_line_amount(i) for i in service_items), Decimal('0'))

    subtotal = version.subtotal or (high_side_total + low_side_total + service_total)
    gst_amount = version.gst_amount or Decimal('0')
    grand_total = version.grand_total or version.total_amount or (subtotal + gst_amount)

    if subtotal and gst_amount:
        gst_percentage = (gst_amount / subtotal) * Decimal('100')
    else:
        gst_percentage = Decimal('18')

    summary_sections = []

    if high_side_items:
        summary_sections.append({
            'title': 'Part A: High Side Equipment',
            'items': [
                {
                    'description': item.description or str(item.product_variant.sku),
                    'amount': _item_line_amount(item),
                }
                for item in high_side_items
            ],
            'subtotal': high_side_total,
        })

    if low_side_items:
        summary_sections.append({
            'title': 'Part B: Low Side Installation Work',
            'items': [
                {
                    'description': item.description or str(item.item.item_code),
                    'amount': _item_line_amount(item),
                }
                for item in low_side_items
            ],
            'subtotal': low_side_total,
        })

    if service_items:
        summary_sections.append({
            'title': 'Part C: Services',
            'items': [
                {
                    'description': f"{item.service.name} ({item.service.category})",
                    'amount': _item_line_amount(item),
                }
                for item in service_items
            ],
            'subtotal': service_total,
        })

    all_items = []

    for item in high_side_items:
        all_items.append({
            'description': item.description or str(item.product_variant.sku),
            'product_variant': item.product_variant,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_line_amount(item),
        })

    for item in low_side_items:
        all_items.append({
            'description': item.description or str(item.item.item_code),
            'item': item.item,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_line_amount(item),
        })

    for item in service_items:
        all_items.append({
            'description': item.description or item.service.name,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_line_amount(item),
        })

    customer = quotation.customer
    site = quotation.site

    return {
        'quotation': quotation,
        'version': version,
        'quotation_no': quotation.quotation_no,
        'quotation_date': version.created_at,
        'customer_name': customer.name if customer else '-',
        'customer_contact': getattr(customer, 'contact_number', '') or '',
        'site_name': (site.site_name if site else None) or quotation.site_name or '-',
        'subject': quotation.subject or '-',
        'summary_sections': summary_sections,
        'quotation_items': all_items,
        'subtotal': subtotal,
        'gst_amount': gst_amount,
        'gst_percentage': gst_percentage,
        'grand_total': grand_total,
        'total_quantity': sum(
            (Decimal(str(item.get('quantity', 0) or 0)) for item in all_items),
            Decimal('0'),
        ),
    }


def generate_quotation_pdf(quotation, version, base_url=None):
    """
    Generate quotation PDF using WeasyPrint with HTML template (existing design).
    """
    try:
        context = _build_quotation_pdf_context(quotation, version)
        html_string = render_to_string('pdf/quotation.html', context)
        pdf = HTML(
            string=html_string,
            base_url=base_url or getattr(settings, 'ABSOLUTE_URL', '/'),
        ).write_pdf()
        return pdf
    except Exception as e:
        logger.error(f"Error generating quotation PDF: {str(e)}", exc_info=True)
        raise


def generate_quotation_print_pdf(quotation, version, base_url=None):
    """
    New WeasyPrint quotation PDF (invoice-style layout).
    Design stage: uses a dummy items table. Existing /pdf/ endpoints unchanged.
    """
    dummy_rows = [
        {
            'sr': 1,
            'description': 'Dummy Item - Copper Pipe 1/2 inch',
            'qty': 10,
            'unit': 'Nos',
            'rate': Decimal('450.00'),
            'amount': Decimal('4500.00'),
        },
        {
            'sr': 2,
            'description': 'Dummy Item - Insulation Tape',
            'qty': 5,
            'unit': 'Nos',
            'rate': Decimal('120.00'),
            'amount': Decimal('600.00'),
        },
        {
            'sr': 3,
            'description': 'Dummy Item - Service Charge',
            'qty': 1,
            'unit': 'Job',
            'rate': Decimal('2500.00'),
            'amount': Decimal('2500.00'),
        },
    ]

    subtotal = sum((row['amount'] for row in dummy_rows), Decimal('0'))
    if version.subtotal and version.gst_amount and version.subtotal > 0:
        gst_pct = (version.gst_amount / version.subtotal) * Decimal('100')
    else:
        gst_pct = Decimal('18')
    gst_amount = (subtotal * gst_pct) / Decimal('100')
    grand_total = subtotal + gst_amount

    context = {
        'quotation': quotation,
        'version': version,
        'dummy_rows': dummy_rows,
        'subtotal': subtotal,
        'gst_amount': gst_amount,
        'grand_total': grand_total,
        'gst_percentage': gst_pct,
    }

    html_string = render_to_string('pdf/quotation_print.html', context)
    pdf = HTML(
        string=html_string,
        base_url=base_url or getattr(settings, 'ABSOLUTE_URL', '/'),
    ).write_pdf()
    return pdf
