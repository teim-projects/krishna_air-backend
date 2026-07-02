# quotation/utils/pdf_generator.py
from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def generate_quotation_pdf(quotation, version):
    """
    Generate quotation PDF using WeasyPrint with HTML template
    
    Args:
        quotation: Quotation model instance
        version: QuotationVersion model instance
    
    Returns:
        PDF bytes content
    """
    
    try:
        # Get all items from version
        high_side_items = version.high_side_items.select_related(
            'product_variant__product_model'
        ).all()
        
        low_side_items = version.low_side_items.select_related(
            'item__material_type_id',
            'item__item_type_id',
            'item__feature_type_id',
            'item__brand'
        ).all()
        
        service_items = version.service_items.all()
        
        # Calculate totals
        high_side_total = sum([item.amount for item in high_side_items], Decimal('0'))
        low_side_total = sum([item.amount for item in low_side_items], Decimal('0'))
        service_total = sum([item.amount for item in service_items], Decimal('0'))
        
        subtotal = high_side_total + low_side_total + service_total
        gst_amount = (subtotal * quotation.gst_percentage) / Decimal('100')
        grand_total = subtotal + gst_amount
        
        # Prepare summary sections
        summary_sections = []
        
        if high_side_items.exists():
            summary_sections.append({
                'title': 'Part A: High Side Equipment',
                'items': [
                    {
                        'description': item.description or f"{item.product_variant.sku}",
                        'amount': item.amount
                    }
                    for item in high_side_items
                ],
                'subtotal': high_side_total
            })
        
        if low_side_items.exists():
            summary_sections.append({
                'title': 'Part B: Low Side Installation Work',
                'items': [
                    {
                        'description': item.description or f"{item.item.item_code}",
                        'amount': item.amount
                    }
                    for item in low_side_items
                ],
                'subtotal': low_side_total
            })
        
        if service_items.exists():
            summary_sections.append({
                'title': 'Part C: Services',
                'items': [
                    {
                        'description': f"{item.service.name} ({item.service.category})",
                        'amount': item.amount
                    }
                    for item in service_items
                ],
                'subtotal': service_total
            })
        
        # Combine all items for BOQ table
        all_items = []
        
        for item in high_side_items:
            all_items.append({
                'description': item.description or f"{item.product_variant.sku}",
                'quantity': item.quantity,
                'unit': item.unit,
                'rate': item.rate,
                'amount': item.amount
            })
        
        for item in low_side_items:
            all_items.append({
                'description': item.description or f"{item.item.item_code}",
                'quantity': item.quantity,
                'unit': item.unit,
                'rate': item.rate,
                'amount': item.amount
            })
        
        for item in service_items:
            all_items.append({
                'description': f"{item.service.name}",
                'quantity': item.quantity,
                'unit': item.unit,
                'rate': item.rate,
                'amount': item.amount
            })
        
        # Context for template
        context = {
            'quotation': quotation,
            'version': version,
            'summary_sections': summary_sections,
            'quotation_items': all_items,
            'subtotal': subtotal,
            'gst_amount': gst_amount,
            'grand_total': grand_total,
            'total_quantity': sum([item.get('quantity', 0) for item in all_items], Decimal('0'))
        }
        
        # Render HTML template
        html_string = render_to_string('pdf/quotation.html', context)
        
        # Generate PDF
        pdf = HTML(
            string=html_string,
            base_url=settings.ABSOLUTE_URL
        ).write_pdf()
        
        return pdf
        
    except Exception as e:
        logger.error(f"Error generating quotation PDF: {str(e)}", exc_info=True)
        raise
