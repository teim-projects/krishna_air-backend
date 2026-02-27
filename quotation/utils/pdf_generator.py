# quotation/utils/pdf_generator.py
import io
from datetime import datetime
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from django.http import HttpResponse


class QuotationPDFGenerator:
    def __init__(self, quotation, version):
        self.quotation = quotation
        self.version = version
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        self.styles = getSampleStyleSheet()
        self.elements = []
        self.setup_styles()

    def setup_styles(self):
        """Setup custom styles for the PDF"""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=2,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='QuotationTitle',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='Address',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_LEFT,
            leading=12
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            spaceBefore=10,
            spaceAfter=5
        ))

        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            spaceBefore=5,
            spaceAfter=3
        ))

        self.styles.add(ParagraphStyle(
            name='Label',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='Value',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            leading=12
        ))

    def add_company_header(self):
        """Add company header"""
        data = [
            [Paragraph("KRISHNA AIRCONDITIONING", self.styles['CompanyName'])],
            [Paragraph("309B, Patil Plaza, Mitra Mandal Chowk,", self.styles['Address'])],
            [Paragraph("Saras Baug, Pune-411 009.", self.styles['Address'])],
            [Paragraph("GSTIN: 27AITPP8825B2ZS | PAN: AITPP8825B", self.styles['Address'])],
        ]
        
        table = Table(data, colWidths=[self.doc.width])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_quotation_title(self):
        """Add quotation title and basic info"""
        self.elements.append(Paragraph("QUOTATION", self.styles['QuotationTitle']))
        
        # Quotation details
        data = [
            [
                Paragraph(f"<b>Quotation No:</b> {self.quotation.quotation_no}", self.styles['Value']),
                Paragraph(f"<b>Date:</b> {self.quotation.created_at.strftime('%d-%m-%Y')}", self.styles['Value'])
            ],
            [
                Paragraph(f"<b>Version:</b> {self.version.version_no}", self.styles['Value']),
                Paragraph(f"<b>Subject:</b> {self.quotation.subject}", self.styles['Value'])
            ],
            [
                Paragraph(f"<b>Site Name:</b> {self.quotation.site_name or 'N/A'}", self.styles['Value']),
                ''
            ]
        ]
        
        table = Table(data, colWidths=[self.doc.width/2.0 - 10, self.doc.width/2.0 - 10])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_customer_details(self):
        """Add customer details"""
        self.elements.append(Paragraph("Customer Details", self.styles['SectionHeader']))
        
        data = [
            [
                Paragraph("<b>Customer Name:</b>", self.styles['Label']),
                Paragraph(self.quotation.customer.name, self.styles['Value'])
            ],
            [
                Paragraph("<b>Contact:</b>", self.styles['Label']),
                Paragraph(self.quotation.customer.contact_number or 'N/A', self.styles['Value'])
            ],
            [
                Paragraph("<b>Address:</b>", self.styles['Label']),
                Paragraph(self.quotation.customer.address or 'N/A', self.styles['Value'])
            ]
        ]
        
        table = Table(data, colWidths=[80, self.doc.width - 100])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    # quotation/utils/pdf_generator.py

# In the add_high_side_items method, replace the product_name section with:

    # quotation/utils/pdf_generator.py

    def add_high_side_items(self):
        """Add high side items table"""
        try:
            high_items = self.version.high_side_items.all()
            if not high_items:
                return
                
            self.elements.append(Paragraph("High Side Items", self.styles['SubHeader']))
            
            # Table headers
            headers = [
                ['Sr.', 'Product', 'Model', 'Capacity', 'Qty', 'Unit Price', 'Mathadi', 'Transport', 'GST%', 'Amount']
            ]
            
            # Table data
            data = headers.copy()
            for idx, item in enumerate(high_items, 1):
                # Get product variant and related product model
                variant = item.product_variant
                product_model = variant.product_model if hasattr(variant, 'product_model') else None
                
                # Product name
                product_name = product_model.name if product_model else 'N/A'
                
                # Model number
                model_no = product_model.model_no if product_model else 'N/A'
                
                # Capacity
                capacity = variant.capacity if hasattr(variant, 'capacity') else 'N/A'
                
                data.append([
                    str(idx),
                    Paragraph(product_name, self.styles['Value']),
                    Paragraph(model_no, self.styles['Value']),
                    capacity,
                    str(item.quantity),
                    f"{float(item.unit_price):,.2f}",
                    f"{float(item.mathadi_charges):,.2f}",
                    f"{float(item.transportation_charges):,.2f}",
                    f"{float(item.gst_percent)}%",
                    f"{float(item.total_with_gst):,.2f}"
                ])
            
            # Subtotal row
            high_subtotal = sum(float(item.total_with_gst) for item in high_items)
            data.append([
                '', '', '', '', '', '', '', '', 
                Paragraph("<b>Subtotal:</b>", self.styles['Value']),
                Paragraph(f"<b>{high_subtotal:,.2f}</b>", self.styles['Value'])
            ])
            
            col_widths = [25, 100, 80, 50, 35, 55, 45, 45, 40, 55]
            table = Table(data, colWidths=col_widths)
            
            style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#BDC3C7')),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#2C3E50')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ECF0F1')),
            ]
            
            table.setStyle(TableStyle(style))
            
            self.elements.append(table)
            self.elements.append(Spacer(1, 10))
        except Exception as e:
            logger.error(f"Error in add_high_side_items: {str(e)}")
            self.elements.append(Paragraph(f"Error loading high side items: {str(e)}", self.styles['Value']))
    # quotation/utils/pdf_generator.py
    
    # Update the add_low_side_items method:

    def add_low_side_items(self):
        """Add low side items table"""
        try:
            low_items = self.version.low_side_items.all()
            if not low_items:
                return
                
            self.elements.append(Paragraph("Low Side Items", self.styles['SubHeader']))
            
            # Table headers
            headers = [
                ['Sr.', 'Item Code', 'Description', 'Qty', 'Unit Price', 'Mathadi', 'GST%', 'Amount']
            ]
            
            # Table data
            data = headers.copy()
            for idx, item in enumerate(low_items, 1):
                # Get item details from the related item model
                item_obj = item.item
                
                # Use item_code as the primary identifier
                item_code = item_obj.item_code if hasattr(item_obj, 'item_code') else 'N/A'
                
                # Build description from available fields
                description_parts = []
                if hasattr(item_obj, 'material_type_id') and item_obj.material_type_id:
                    description_parts.append(str(item_obj.material_type_id))
                if hasattr(item_obj, 'item_type_id') and item_obj.item_type_id:
                    description_parts.append(str(item_obj.item_type_id))
                if hasattr(item_obj, 'feature_type_id') and item_obj.feature_type_id:
                    description_parts.append(str(item_obj.feature_type_id))
                if hasattr(item_obj, 'size') and item_obj.size:
                    size_str = f"{item_obj.size}{item_obj.size_unit or ''}"
                    description_parts.append(size_str)
                if hasattr(item_obj, 'brand') and item_obj.brand:
                    description_parts.append(str(item_obj.brand))
                    
                description = ' - '.join(description_parts) if description_parts else 'N/A'
                
                data.append([
                    str(idx),
                    Paragraph(item_code, self.styles['Value']),
                    Paragraph(description, self.styles['Value']),
                    str(item.quantity),
                    f"{float(item.unit_price):,.2f}",
                    f"{float(item.mathadi_charges):,.2f}",
                    f"{float(item.gst_percent)}%",
                    f"{float(item.total_with_gst):,.2f}"
                ])
            
            # Subtotal row
            low_subtotal = sum(float(item.total_with_gst) for item in low_items)
            data.append([
                '', '', '', '', '', '', 
                Paragraph("<b>Subtotal:</b>", self.styles['Value']),
                Paragraph(f"<b>{low_subtotal:,.2f}</b>", self.styles['Value'])
            ])
            
            col_widths = [25, 100, 150, 35, 55, 45, 40, 65]
            table = Table(data, colWidths=col_widths)
            
            style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (2, -1), 'LEFT'),  # Item Code and Description left-aligned
                ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Numbers right-aligned
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#BDC3C7')),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#2C3E50')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ECF0F1')),
            ]
            
            table.setStyle(TableStyle(style))
            
            self.elements.append(table)
            self.elements.append(Spacer(1, 10))
        except Exception as e:
            logger.error(f"Error in add_low_side_items: {str(e)}")
            # Add a simple error message
            self.elements.append(Paragraph(f"Error loading low side items: {str(e)}", self.styles['Value']))


    def add_tax_summary(self):
        """Add tax summary section"""
        self.elements.append(Paragraph("Tax Summary", self.styles['SectionHeader']))
        
        if self.version.gst_type == "CGST_SGST":
            data = [
                ['Description', 'Subtotal', 'CGST (9%)', 'SGST (9%)', 'Total Tax', 'Grand Total'],
                [
                    'Total',
                    f"{self.version.subtotal:,.2f}",
                    f"{self.version.cgst_amount:,.2f}",
                    f"{self.version.sgst_amount:,.2f}",
                    f"{self.version.gst_amount:,.2f}",
                    f"{self.version.grand_total:,.2f}"
                ]
            ]
            col_widths = [80, 70, 70, 70, 70, 80]
        else:
            data = [
                ['Description', 'Subtotal', 'IGST (18%)', 'Total Tax', 'Grand Total'],
                [
                    'Total',
                    f"{self.version.subtotal:,.2f}",
                    f"{self.version.igst_amount:,.2f}",
                    f"{self.version.gst_amount:,.2f}",
                    f"{self.version.grand_total:,.2f}"
                ]
            ]
            col_widths = [80, 100, 100, 100, 100]
        
        table = Table(data, colWidths=col_widths)
        
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#EBF5FB')),
        ]
        
        table.setStyle(TableStyle(style))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_terms_and_conditions(self):
        """Add terms and conditions"""
        self.elements.append(Paragraph("Terms and Conditions", self.styles['SectionHeader']))
        
        terms = [
            "1. This quotation is valid for 30 days from the date of issue.",
            "2. Payment terms: 50% advance and 50% before delivery.",
            "3. GST extra as applicable.",
            "4. Transportation and installation charges extra.",
            "5. Warranty as per manufacturer's terms and conditions.",
        ]
        
        for term in terms:
            self.elements.append(Paragraph(term, self.styles['Value']))
        
        self.elements.append(Spacer(1, 10))
        
        # Thank you note
        if self.quotation.thank_you_note:
            self.elements.append(Paragraph(
                self.quotation.thank_you_note,
                ParagraphStyle(
                    name='ThankYou',
                    parent=self.styles['Value'],
                    alignment=TA_CENTER,
                    textColor=colors.HexColor('#27AE60'),
                    fontName='Helvetica-Bold'
                )
            ))
            self.elements.append(Spacer(1, 10))

    def add_footer(self):
        """Add footer with signature"""
        data = [
            [
                Paragraph("<b>For Krishna Airconditioning</b>", self.styles['Value']),
                ''
            ],
            [
                Paragraph("Authorised Signatory", self.styles['Label']),
                Paragraph("(This is a Computer Generated Quotation)", self.styles['Label'])
            ]
        ]
        
        table = Table(data, colWidths=[self.doc.width/2, self.doc.width/2])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LINEABOVE', (0, 1), (-1, 1), 1, colors.HexColor('#2C3E50')),
        ]))
        
        self.elements.append(table)

    def number_to_words(self, number):
        """Convert number to words (simplified version)"""
        num = int(number)
        if num < 1000:
            return f"Rupees {num} Only"
        elif num < 100000:
            return f"Rupees {num/1000:.1f} Thousand Only"
        else:
            return f"Rupees {num/100000:.1f} Lakh Only"

    def generate(self):
        """Generate the PDF"""
        self.add_company_header()
        self.add_quotation_title()
        self.add_customer_details()
        self.add_high_side_items()
        self.add_low_side_items()
        self.add_tax_summary()
        self.add_terms_and_conditions()
        self.add_footer()
        
        self.doc.build(self.elements)
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf


def generate_quotation_pdf(quotation, version):
    """Generate PDF for quotation"""
    generator = QuotationPDFGenerator(quotation, version)
    return generator.generate()