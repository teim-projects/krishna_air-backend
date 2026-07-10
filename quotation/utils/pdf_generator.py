# quotation/utils/pdf_generator.py
from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _format_capacity(product_variant):
    capacity = getattr(product_variant, 'capacity', None)
    if capacity in (None, ''):
        return ''

    capacity_text = str(capacity).strip()
    
    # Strip any duplicate unit suffix entered in the capacity field (e.g. "1.0TR" -> "1.0")
    for suffix in ['TR', 'TON', 'T']:
        if capacity_text.upper().endswith(suffix):
            idx = capacity_text.upper().rfind(suffix)
            capacity_text = capacity_text[:idx].strip()
            break

    unit = (getattr(product_variant, 'unit', '') or '').strip().upper()
    unit_label_map = {
        'TR': 'TR',
        'TON': 'Ton',
        'T': 'TR',
    }
    unit_label = unit_label_map.get(unit, 'TR')  # Default to 'TR'

    return f"{capacity_text} {unit_label}".strip()


def _high_side_description(item):
    product_variant = getattr(item, 'product_variant', None)
    if not product_variant:
        return 'High Side Equipment'

    product_model = getattr(product_variant, 'product_model', None)
    ac_sub_type = getattr(product_model, 'ac_sub_type_id', None) if product_model else None
    ac_type = getattr(ac_sub_type, 'ac_type_id', None) if ac_sub_type else None

    parts = []

    # 1. AC Type (e.g. Split AC)
    ac_type_name = getattr(ac_type, 'name', None)
    if ac_type_name:
        parts.append(ac_type_name)

    # 2. Capacity (e.g. 1.0 TR / 2.2 TR)
    capacity_text = _format_capacity(product_variant)
    if capacity_text:
        parts.append(capacity_text)

    # 3. Star Rating (e.g. 3 Star / 4 Star)
    star_rating = getattr(product_variant, 'star_rating', None)
    if star_rating:
        parts.append(f"{star_rating} Star")

    # 4. Inverter Status (Inverter / Non-Inverter)
    inverter = getattr(product_model, 'inverter', None) if product_model else None
    if inverter is True:
        parts.append('Inverter')
    elif inverter is False:
        parts.append('Non-Inverter')

    return ' '.join(parts) if parts else 'High Side Equipment'


def _low_side_description(item):
    if item.description and item.description.strip():
        return item.description.strip()

    low_item = getattr(item, 'item', None)
    if not low_item:
        return 'Low Side Item'

    parts = []
    
    material = getattr(low_item, 'material_type_id', None)
    if material and getattr(material, 'name', None):
        parts.append(material.name.strip())

    item_type_obj = getattr(low_item, 'item_type_id', None)
    if item_type_obj and getattr(item_type_obj, 'name', None):
        parts.append(item_type_obj.name.strip())

    feature = getattr(low_item, 'feature_type_id', None)
    if feature and getattr(feature, 'name', None):
        parts.append(feature.name.strip())

    item_class_obj = getattr(low_item, 'item_class_id', None)
    if item_class_obj and getattr(item_class_obj, 'name', None):
        parts.append(item_class_obj.name.strip())

    if getattr(low_item, 'size', None):
        size_str = f"{low_item.size} {low_item.size_unit or ''}".strip()
        parts.append(size_str)

    if getattr(low_item, 'thickness', None):
        thick_str = f"{low_item.thickness} {low_item.thickness_unit or ''}".strip()
        parts.append(thick_str)

    return " ".join(parts) if parts else getattr(low_item, 'item_code', 'Low Side Item')


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


def _classify_high_side_item(item):
    variant = getattr(item, 'product_variant', None)
    if not variant:
        return 'ACCESSORIES'

    model = getattr(variant, 'product_model', None)
    if not model:
        return 'ACCESSORIES'

    sub_type = getattr(model, 'ac_sub_type_id', None)
    sub_type_name = getattr(sub_type, 'name', '').upper() if sub_type else ''
    model_name = getattr(model, 'name', '').upper()
    sku = getattr(variant, 'sku', '').upper()

    # 1. Outdoor/Condensing Units
    if getattr(model, 'model_no_odu', None) or 'ODU' in sku or 'ODU' in sub_type_name or 'CONDENSING' in model_name or 'OUTDOOR' in model_name:
        return 'ODU'

    # 2. Indoor Units
    if getattr(model, 'model_no_idu', None) or 'IDU' in sku or 'IDU' in sub_type_name or 'INDOOR' in model_name or 'CASSETTE' in model_name or 'HI-WALL' in model_name:
        return 'IDU'

    # 3. Controllers
    if 'REMOTE' in sku or 'CONTROLLER' in sku or 'REMOTE' in model_name or 'CONTROLLER' in model_name or 'REMOTE' in sub_type_name:
        return 'CONTROLLER'

    # 4. Refnet Joints / Piping joints
    if 'JOINT' in sku or 'REFNET' in sku or 'JOINT' in model_name or 'REFNET' in model_name:
        return 'JOINT'

    return 'ACCESSORIES'


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

    high_side_total = sum((_item_base_amount(i) for i in high_side_items), Decimal('0'))
    low_side_total = sum((_item_base_amount(i) for i in low_side_items), Decimal('0'))
    service_total = sum((_item_base_amount(i) for i in service_items), Decimal('0'))

    high_side_grand_total = sum((i.total_with_gst for i in high_side_items), Decimal('0'))
    low_side_grand_total = sum((i.total_with_gst for i in low_side_items), Decimal('0'))
    service_grand_total = sum((i.total_with_gst for i in service_items), Decimal('0'))

    # Group High Side Items by AC Type for proposal summary
    high_side_groups = {}
    for item in high_side_items:
        product_variant = getattr(item, 'product_variant', None)
        product_model = getattr(product_variant, 'product_model', None) if product_variant else None
        ac_sub_type = getattr(product_model, 'ac_sub_type_id', None) if product_model else None
        ac_type = getattr(ac_sub_type, 'ac_type_id', None) if ac_sub_type else None
        ac_type_name = getattr(ac_type, 'name', None) if ac_type else None
        
        if not ac_type_name:
            ac_type_name = "AC Equipment"
        
        ac_type_name = ac_type_name.strip().upper()
        amount = _item_base_amount(item)
        high_side_groups[ac_type_name] = high_side_groups.get(ac_type_name, Decimal('0')) + amount

    high_side_summary = [
        {'description': name, 'amount': amount}
        for name, amount in high_side_groups.items()
    ]

    # Group Low Side Items by Item Type for proposal summary
    low_side_groups = {}
    for item in low_side_items:
        item_obj = getattr(item, 'item', None)
        item_type = getattr(item_obj, 'item_type_id', None) if item_obj else None
        item_type_name = getattr(item_type, 'name', None) if item_type else None
        
        if not item_type_name:
            item_type_name = "MISCELLANEOUS WORK"
            
        item_type_name = item_type_name.strip().upper()
        amount = _item_base_amount(item)
        low_side_groups[item_type_name] = low_side_groups.get(item_type_name, Decimal('0')) + amount

    low_side_summary = [
        {'description': name, 'amount': amount}
        for name, amount in low_side_groups.items()
    ]

    # Group Service Items by Category for proposal summary
    service_groups = {}
    for item in service_items:
        service_obj = getattr(item, 'service', None)
        category_name = getattr(service_obj, 'category', None) if service_obj else 'SERVICES'
        category_name = str(category_name).strip().upper()
        amount = _item_base_amount(item)
        service_groups[category_name] = service_groups.get(category_name, Decimal('0')) + amount

    service_summary = [
        {'description': name, 'amount': amount}
        for name, amount in service_groups.items()
    ]

    # Classify and group high side items for BOQ
    odus = []
    idus = []
    controllers = []
    joints = []
    accessories = []

    for item in high_side_items:
        category = _classify_high_side_item(item)
        variant = item.product_variant
        ac_type_name_val = None
        if variant and variant.product_model and variant.product_model.ac_sub_type_id and variant.product_model.ac_sub_type_id.ac_type_id:
            ac_type_name_val = variant.product_model.ac_sub_type_id.ac_type_id.name
            
        item_data = {
            'description': _high_side_description(item),
            'product_variant': item.product_variant,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_base_amount(item),
            'sku': getattr(item.product_variant, 'sku', ''),
            'ac_type': ac_type_name_val or "AC Equipment"
        }
        if category == 'ODU':
            odus.append(item_data)
        elif category == 'IDU':
            sub_type = getattr(item.product_variant.product_model, 'ac_sub_type_id', None)
            item_data['sub_type_name'] = getattr(sub_type, 'name', 'Indoor Unit')
            idus.append(item_data)
        elif category == 'CONTROLLER':
            controllers.append(item_data)
        elif category == 'JOINT':
            joints.append(item_data)
        else:
            accessories.append(item_data)

    # Group IDUs by sub_type_name
    idu_groups = []
    from collections import defaultdict
    grouped_idus = defaultdict(list)
    for item in idus:
        grouped_idus[item['sub_type_name']].append(item)
    
    for sub_name, items in grouped_idus.items():
        idu_groups.append({
            'sub_type_name': sub_name,
            'items': items
        })

    ac_type_names = []
    for item in high_side_items:
        variant = getattr(item, 'product_variant', None)
        product_model = getattr(variant, 'product_model', None) if variant else None
        ac_sub_type = getattr(product_model, 'ac_sub_type_id', None) if product_model else None
        ac_type = getattr(ac_sub_type, 'ac_type_id', None) if ac_sub_type else None
        ac_type_name_val = getattr(ac_type, 'name', None) if ac_type else None
        if ac_type_name_val:
            ac_type_name_val = ac_type_name_val.strip()
            if ac_type_name_val not in ac_type_names:
                ac_type_names.append(ac_type_name_val)
    ac_type_name = " / ".join(ac_type_names) if ac_type_names else "Air Conditioning"

    subtotal = version.subtotal or (high_side_total + low_side_total + service_total)
    gst_amount = version.gst_amount or Decimal('0')
    grand_total = version.grand_total or version.total_amount or (subtotal + gst_amount)

    if subtotal and gst_amount:
        gst_percentage = (gst_amount / subtotal) * Decimal('100')
    else:
        gst_percentage = Decimal('18')

    all_items = []

    for item in high_side_items:
        all_items.append({
            'description': _high_side_description(item),
            'product_variant': item.product_variant,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_base_amount(item),
        })

    for item in low_side_items:
        all_items.append({
            'description': item.description or str(item.item.item_code),
            'item': item.item,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_base_amount(item),
        })

    for item in service_items:
        all_items.append({
            'description': item.description or item.service.name,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_base_amount(item),
        })

    customer = quotation.customer
    site = quotation.site
    site_name = (
        getattr(site, 'name', None)
        or getattr(site, 'site_name', None)
        or quotation.site_name
        or '-'
    )

    summary_sections = []

    if high_side_items:
        summary_sections.append({
            'title': 'Part A: High Side Air Conditioning Equipment',
            'items': [
                {
                    'description': _high_side_description(item),
                    'amount': _item_base_amount(item),
                }
                for item in high_side_items
            ],
            'total': high_side_total,
            'gst_amount': sum((getattr(i, 'gst_amount', Decimal('0')) or Decimal('0') for i in high_side_items), Decimal('0')),
            'subtotal_with_gst': high_side_grand_total,
        })

    if low_side_items:
        summary_sections.append({
            'title': 'Part B: Low Side Installation Work',
            'items': [
                {
                    'description': _low_side_description(item),
                    'amount': _item_base_amount(item),
                }
                for item in low_side_items
            ],
            'total': low_side_total,
            'gst_amount': sum((getattr(i, 'gst_amount', Decimal('0')) or Decimal('0') for i in low_side_items), Decimal('0')),
            'subtotal_with_gst': low_side_grand_total,
        })

    if service_items:
        summary_sections.append({
            'title': 'Part C: Services',
            'items': [
                {
                    'description': f"{item.service.name} ({item.service.category})",
                    'amount': _item_base_amount(item),
                }
                for item in service_items
            ],
            'total': service_total,
            'gst_amount': sum((getattr(i, 'gst_amount', Decimal('0')) or Decimal('0') for i in service_items), Decimal('0')),
            'subtotal_with_gst': service_grand_total,
        })

    # Group High Side Items by AC Type for table separation
    def _get_ac_type_name(item):
        variant = getattr(item, 'product_variant', None)
        product_model = getattr(variant, 'product_model', None) if variant else None
        ac_sub_type = getattr(product_model, 'ac_sub_type_id', None) if product_model else None
        ac_type = getattr(ac_sub_type, 'ac_type_id', None) if ac_sub_type else None
        ac_type_name = getattr(ac_type, 'name', None) if ac_type else None
        return ac_type_name.strip() if ac_type_name else "AC Equipment"

    high_side_by_type = {}
    for item in high_side_items:
        t_name = _get_ac_type_name(item)
        if t_name not in high_side_by_type:
            high_side_by_type[t_name] = []
        high_side_by_type[t_name].append({
            'description': _high_side_description(item),
            'product_variant': item.product_variant,
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_base_amount(item),
            'gst_amount': getattr(item, 'gst_amount', 0) or 0,
            'gst_percent': getattr(item, 'gst_percent', 18),
            'sku': getattr(item.product_variant, 'sku', '')
        })

    high_side_groups = []
    for t_name, items in high_side_by_type.items():
        sub_total_val = sum(i['amount'] for i in items)
        gst_total_val = sum(i['gst_amount'] for i in items)
        gst_percent_val = items[0]['gst_percent'] if items else 18
        high_side_groups.append({
            'ac_type': t_name,
            'items': items,
            'subtotal': sub_total_val,
            'gst_total': gst_total_val,
            'gst_percent': gst_percent_val,
            'total_with_gst': sub_total_val + gst_total_val,
        })

    # Group Low Side Items by AC Type using AcMaterials
    from product_management.models import AcMaterials
    material_to_ac_types = {}
    for am in AcMaterials.objects.select_related('ac_type', 'material').all():
        m_id = am.material_id
        t_name = am.ac_type.name.strip()
        if m_id not in material_to_ac_types:
            material_to_ac_types[m_id] = []
        material_to_ac_types[m_id].append(t_name)

    low_side_by_type = {}
    for item in low_side_items:
        assigned_type = None
        item_obj = item.item
        if item_obj and item_obj.id in material_to_ac_types:
            for t_name in material_to_ac_types[item_obj.id]:
                if t_name in high_side_by_type:
                    assigned_type = t_name
                    break
            if not assigned_type:
                assigned_type = material_to_ac_types[item_obj.id][0]
        if not assigned_type:
            assigned_type = list(high_side_by_type.keys())[0] if high_side_by_type else "AC Equipment"
            
        if assigned_type not in low_side_by_type:
            low_side_by_type[assigned_type] = []
        low_side_by_type[assigned_type].append({
            'description': _low_side_description(item),
            'quantity': item.quantity,
            'unit': item.unit,
            'rate': item.unit_price,
            'amount': _item_base_amount(item),
            'gst_amount': getattr(item, 'gst_amount', 0) or 0,
            'gst_percent': getattr(item, 'gst_percent', 18),
        })

    low_side_groups = []
    for t_name, items in low_side_by_type.items():
        sub_total_val = sum(i['amount'] for i in items)
        gst_total_val = sum(i['gst_amount'] for i in items)
        gst_percent_val = items[0]['gst_percent'] if items else 18
        low_side_groups.append({
            'ac_type': t_name,
            'items': items,
            'subtotal': sub_total_val,
            'gst_total': gst_total_val,
            'gst_percent': gst_percent_val,
            'total_with_gst': sub_total_val + gst_total_val,
        })

    # Group terms & conditions by category type
    terms_by_type = {}
    for term in quotation.terms_conditions.select_related('terms_condition_type').all():
        t_type = term.terms_condition_type.name if term.terms_condition_type else "Other"
        if t_type not in terms_by_type:
            terms_by_type[t_type] = []
        terms_by_type[t_type].append(term.terms)

    # Already calculated early in this function: high_side_grand_total, low_side_grand_total

    return {
        'high_side_groups': high_side_groups,
        'low_side_groups': low_side_groups,
        'payment_terms': terms_by_type.get("Quotation Payment", []),
        'validity_terms': terms_by_type.get("Quotation Validity", []),
        'warranty_terms': terms_by_type.get("Quotation Warranty", []),
        'other_terms': terms_by_type.get("Quotation Other", []),
        'declaration': getattr(quotation, 'declaration', ''),
        'quotation': quotation,
        'version': version,
        'quotation_no': quotation.quotation_no,
        'quotation_date': version.created_at,
        'customer_name': customer.name if customer else '-',
        'customer_contact': getattr(customer, 'contact_number', '') or '',
        'site_name': site_name,
        'subject': quotation.subject or '-',
        'high_side_summary': high_side_summary,
        'low_side_summary': low_side_summary,
        'service_summary': service_summary,
        'high_side_total': high_side_total,
        'low_side_total': low_side_total,
        'high_side_grand_total': high_side_grand_total,
        'low_side_grand_total': low_side_grand_total,
        'service_total': service_total,
        'grand_total_without_gst': high_side_total + low_side_total + service_total,
        'ac_type_name': ac_type_name,
        'odus': odus,
        'idu_groups': idu_groups,
        'controllers': controllers,
        'joints': joints,
        'accessories': accessories,
        'low_side_items': [
            {
                'description': _low_side_description(item),
                'quantity': item.quantity,
                'unit': item.unit,
                'rate': item.unit_price,
                'amount': _item_base_amount(item),
            }
            for item in low_side_items
        ],
        'high_side_items_list': [
            {
                'description': _high_side_description(item),
                'product_variant': item.product_variant,
                'quantity': item.quantity,
                'unit': item.unit,
                'rate': item.unit_price,
                'amount': _item_base_amount(item),
                'sku': getattr(item.product_variant, 'sku', ''),
                'ac_type': (
                    item.product_variant.product_model.ac_sub_type_id.ac_type_id.name
                    if (item.product_variant and
                        item.product_variant.product_model and
                        item.product_variant.product_model.ac_sub_type_id and
                        item.product_variant.product_model.ac_sub_type_id.ac_type_id)
                    else "AC Equipment"
                )
            }
            for item in high_side_items
        ],
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
