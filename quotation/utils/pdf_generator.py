# quotation/utils/pdf_generator.py
# Updated: 2026-03-10 - Match exact format from screenshots
import io
import logging
import os
from datetime import datetime
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from django.http import HttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)


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
            bottomMargin=15*mm,
            showBoundary=1
        )
        self.styles = getSampleStyleSheet()
        self.elements = []
        self.setup_styles()

    def setup_styles(self):
        """Setup custom styles for the PDF"""
        # Company name in blue
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#0066CC'),
            alignment=TA_LEFT,
            spaceAfter=2,
            fontName='Helvetica-Bold'
        ))
        
        # Contact details in blue
        self.styles.add(ParagraphStyle(
            name='ContactInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#0066CC'),
            alignment=TA_LEFT,
            leading=11
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
            fontSize=11,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
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
        
        # Underlined label style
        self.styles.add(ParagraphStyle(
            name='UnderlinedLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            leading=14
        ))

    def add_company_header(self):
        """Add company header with logo space and contact info"""
        # Get branch information
        if self.quotation.branch:
            branch = self.quotation.branch
            company_name = branch.name
            address = branch.address
            city_state = f"{branch.city}, {branch.state} - {branch.pincode}"
            email = branch.email
            
            # Build address string
            full_address = f"{address}<br/>{city_state}<br/>E-mail: {email}"
        else:
            # Fallback to default
            company_name = "KRISNA AIR CONDITIONING"
            full_address = "309/B, Patil Plaza, Saras Baug, Pune - 411 009.<br/>E-mail: sales@krisnatech.com ; krisnatech@vsnl.in"
        
        # Main header with logo space (left) and company details (right)
        # Try to load logo, fallback to placeholder if not found
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
        
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=80, height=60)  # Adjust size as needed
            except:
                logo = Paragraph('[LOGO]<br/><font size="8">Logo file found but could not load</font>', 
                               ParagraphStyle(name='LogoError', fontSize=10, textColor=colors.red, alignment=TA_CENTER))
        else:
            logo = Paragraph('[LOGO SPACE]<br/><font size="8">Put logo.png in static/images/</font>', 
                           ParagraphStyle(name='LogoPlaceholder', fontSize=10, textColor=colors.grey, alignment=TA_CENTER))
        
        header_data = [
            [
                # Left side - Logo or placeholder
                logo,
                
                # Right side - Dynamic company name and address
                Paragraph(f'<b>{company_name}</b><br/>'
                         f'<font size="9">{full_address}</font>', 
                         ParagraphStyle(name='CompanyHeader', fontSize=12, fontName='Helvetica-Bold', alignment=TA_RIGHT))
            ]
        ]
        
        header_table = Table(header_data, colWidths=[self.doc.width*0.3, self.doc.width*0.7])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),  # Logo space centered
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),   # Company details right-aligned
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        self.elements.append(header_table)
        self.elements.append(Spacer(1, 10))
        
        # Quotation reference and date
        ref_data = [
            [
                '',  # Empty left column
                Paragraph(f'Ref. No: {self.quotation.quotation_no}<br/>{self.quotation.created_at.strftime("%d-%m-%Y")}', 
                         ParagraphStyle(name='RefStyle', fontSize=9, alignment=TA_RIGHT))
            ]
        ]
        
        ref_table = Table(ref_data, colWidths=[self.doc.width*0.7, self.doc.width*0.3])
        ref_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        self.elements.append(ref_table)
        self.elements.append(Spacer(1, 10))

    def add_quotation_title(self):
        """Add To, From, Subject section with dynamic branch and site info"""
        
        # Get branch information for "From" section
        if self.quotation.branch:
            branch_info = f"{self.quotation.branch.name}, {self.quotation.branch.city}"
        else:
            branch_info = "Pune"  # Default fallback
        
        # Get site information
        site_info = ""
        if self.quotation.site:
            site_info = f"{self.quotation.site.name} - {self.quotation.site.address}, {self.quotation.site.city}"
        elif self.quotation.site_name:
            site_info = self.quotation.site_name
        
        # To, From, Subject section
        data = [
            [Paragraph('<u><b>To,</b></u>', self.styles['UnderlinedLabel']), ''],
            [Paragraph(f'<b>From,</b>', self.styles['Label']), ''],
            [Paragraph(f'<b>{branch_info}:</b>', self.styles['Label']), ''],
            [Paragraph(f'<u><b>Subject:</b></u> {self.quotation.subject}', self.styles['UnderlinedLabel']), ''],
        ]
        
        table = Table(data, colWidths=[self.doc.width, 0])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))
        
        # Site Name section (if site information exists)
        if site_info:
            self.elements.append(Paragraph(f'<u><b>Site Name:</b></u> {site_info}', self.styles['UnderlinedLabel']))
            self.elements.append(Spacer(1, 10))
        
        # Greeting
        self.elements.append(Paragraph('Dear Sir,', self.styles['Value']))
        self.elements.append(Spacer(1, 5))
        
        # Introduction text - only use thank_you_note if available
        if self.quotation.thank_you_note:
            intro_text = self.quotation.thank_you_note
            self.elements.append(Paragraph(intro_text, self.styles['Value']))
            self.elements.append(Spacer(1, 10))

    def add_customer_details(self):
        """Add customer details - removed"""
        pass

    def add_high_side_items(self):
        """Add high side items table"""
        try:
            high_items = self.version.high_side_items.all()
            if not high_items:
                return
                
            self.elements.append(Paragraph("High side Installation work", self.styles['SubHeader']))
            
            # Table headers
            headers = [
                ['S.N', 'Description', 'Unit', 'Qty', 'Rate', 'Amount']
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
                
                # Build description with product info and additional description
                product_info = f"{product_name} {model_no} {capacity}"
                
                # Add item description if it exists
                if item.description and item.description.strip():
                    full_description = f"{product_info}<br/><i><font color='grey' size='8'>{item.description}</font></i>"
                else:
                    full_description = product_info
                
                # Main product row with description included in same cell
                data.append([
                    str(idx),
                    Paragraph(full_description, self.styles['Value']),
                    'Nos.',
                    str(item.quantity),
                    f"{float(item.unit_price):,.2f}",
                    f"{float(item.total_with_gst):,.2f}"
                ])
            
            # Add empty row between content and totals
            data.append(['', '', '', '', '', ''])
            
            # Calculate subtotal
            high_subtotal = sum(float(item.total_with_gst) for item in high_items)
            
            # Summary section - High side specific rows
            data.append([
                "Subtotal :", '', '', '', '', 
                f"{high_subtotal:,.2f}"
            ])
            
            # Calculate GST (18%)
            gst_amount = high_subtotal * 0.18
            data.append([
                "GST @ 18% :", '', '', '', '', 
                f"{gst_amount:,.2f}"
            ])
            
            data.append([
                "Mathadi Charges :", '', '', '', '', 
                "Extra"
            ])
            
            data.append([
                "Transportation :", '', '', '', '', 
                "Extra"
            ])
            
            # Calculate total with GST
            total_with_gst = high_subtotal + gst_amount
            data.append([
                "Total :", '', '', '', '', 
                f"{total_with_gst:,.2f}"
            ])

            col_widths = [25, 200, 40, 30, 70, 70]
            table = Table(data, colWidths=col_widths)
            
            # Count data rows (excluding header)
            data_rows = len(data) - 1
            
            empty_row_index = data_rows - 5  # Empty row is 6th from last
            summary_start = data_rows - 4    # Summary rows start (Subtotal, GST, Mathadi, Transportation, Total)
            
            style = [
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header bold
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),   # S.N column center
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),     # Description column left
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),   # Unit, Qty, Rate, Amount right
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                
                # Summary section spans - individual spans for each row to preserve horizontal lines
                ('SPAN', (0, summary_start), (4, summary_start)),      # Subtotal row
                ('SPAN', (0, summary_start+1), (4, summary_start+1)),  # GST row
                ('SPAN', (0, summary_start+2), (4, summary_start+2)),  # Mathadi row
                ('SPAN', (0, summary_start+3), (4, summary_start+3)),  # Transportation row
                ('SPAN', (0, summary_start+4), (4, summary_start+4)),  # Total row
                
                ('ALIGN', (0, summary_start), (4, summary_start+4), 'RIGHT'),  # Labels right-aligned
                ('ALIGN', (5, summary_start), (5, summary_start+4), 'RIGHT'),  # Amounts right-aligned
                ('FONTNAME', (0, summary_start), (-1, summary_start+4), 'Helvetica-Bold'),
                
                # Light gray background for summary rows
                ('BACKGROUND', (0, summary_start), (-1, summary_start+4), colors.HexColor('#F0F0F0')),
                # No background for empty row
                ('BACKGROUND', (0, empty_row_index), (-1, empty_row_index), colors.white),
                
                # Ensure horizontal lines between summary rows are visible
                ('LINEBELOW', (0, summary_start), (-1, summary_start), 0.5, colors.black),
                ('LINEBELOW', (0, summary_start+1), (-1, summary_start+1), 0.5, colors.black),
                ('LINEBELOW', (0, summary_start+2), (-1, summary_start+2), 0.5, colors.black),
                ('LINEBELOW', (0, summary_start+3), (-1, summary_start+3), 0.5, colors.black),
            ]
            
            table.setStyle(TableStyle(style))
            
            self.elements.append(table)
            self.elements.append(Spacer(1, 10))
        except Exception as e:
            logger.error(f"Error in add_high_side_items: {str(e)}")
            self.elements.append(Paragraph(f"Error loading high side items: {str(e)}", self.styles['Value']))

    def add_low_side_items(self):
        """Add low side items table"""
        try:
            low_items = self.version.low_side_items.all()
            if not low_items:
                return

            self.elements.append(Paragraph("Low side Installation work", self.styles['SubHeader']))

            # Table headers
            headers = [
                ['S.N', 'Description', 'Unit', 'Qty', 'Rate', 'Amount']
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

                product_info = ' - '.join(description_parts) if description_parts else 'N/A'
                
                # Add item description if it exists
                if item.description and item.description.strip():
                    full_description = f"{product_info}<br/><i><font color='grey' size='8'>{item.description}</font></i>"
                else:
                    full_description = product_info

                # Main product row with description included in same cell
                data.append([
                    str(idx),
                    Paragraph(full_description, self.styles['Value']),
                    'Nos.',
                    str(item.quantity),
                    f"{float(item.unit_price):,.2f}",
                    f"{float(item.total_with_gst):,.2f}"
                ])

            # Add empty row between content and totals
            data.append(['', '', '', '', '', ''])
            
            # Calculate subtotal
            low_subtotal = sum(float(item.total_with_gst) for item in low_items)
            
            # Summary section - Low side specific rows
            data.append([
                "Subtotal :", '', '', '', '', 
                f"{low_subtotal:,.2f}"
            ])
            
            # Calculate GST (18%)
            gst_amount = low_subtotal * 0.18
            data.append([
                "GST @ 18% :", '', '', '', '', 
                f"{gst_amount:,.2f}"
            ])
            
            data.append([
                "Mathadi Charges :", '', '', '', '', 
                "Extra"
            ])
            
            # Calculate total with GST
            total_with_gst = low_subtotal + gst_amount
            data.append([
                "Total :", '', '', '', '', 
                f"{total_with_gst:,.2f}"
            ])

            col_widths = [25, 200, 40, 30, 70, 70]
            table = Table(data, colWidths=col_widths)
            
            # Count data rows (excluding header)
            data_rows = len(data) - 1
            
            empty_row_index = data_rows - 4  # Empty row is 5th from last
            summary_start = data_rows - 3    # Summary rows start (Subtotal, GST, Mathadi, Total) - 4 rows total

            style = [
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header bold
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),   # S.N column center
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),     # Description column left
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),   # Unit, Qty, Rate, Amount right
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                
                # Summary section spans - individual spans for each row to preserve horizontal lines
                ('SPAN', (0, summary_start), (4, summary_start)),      # Subtotal row
                ('SPAN', (0, summary_start+1), (4, summary_start+1)),  # GST row
                ('SPAN', (0, summary_start+2), (4, summary_start+2)),  # Mathadi row
                ('SPAN', (0, summary_start+3), (4, summary_start+3)),  # Total row
                
                ('ALIGN', (0, summary_start), (4, summary_start+3), 'RIGHT'),  # Labels right-aligned
                ('ALIGN', (5, summary_start), (5, summary_start+3), 'RIGHT'),  # Amounts right-aligned
                ('FONTNAME', (0, summary_start), (-1, summary_start+3), 'Helvetica-Bold'),
                
                # Light gray background for summary rows
                ('BACKGROUND', (0, summary_start), (-1, summary_start+3), colors.HexColor('#F0F0F0')),
                # No background for empty row
                ('BACKGROUND', (0, empty_row_index), (-1, empty_row_index), colors.white),
                
                # Ensure horizontal lines between summary rows are visible
                ('LINEBELOW', (0, summary_start), (-1, summary_start), 0.5, colors.black),
                ('LINEBELOW', (0, summary_start+1), (-1, summary_start+1), 0.5, colors.black),
                ('LINEBELOW', (0, summary_start+2), (-1, summary_start+2), 0.5, colors.black),
            ]

            table.setStyle(TableStyle(style))

            self.elements.append(table)

            # Add page break if more than 4 items
            if len(low_items) >= 4:
                self.elements.append(PageBreak())
            else:
                self.elements.append(Spacer(1, 10))
        except Exception as e:
            logger.error(f"Error in add_low_side_items: {str(e)}")
            self.elements.append(Paragraph(f"Error loading low side items: {str(e)}", self.styles['Value']))


    def add_tax_summary(self):
        """Add tax summary section - removed as per screenshot"""
        pass

    def add_terms_and_conditions(self):
        """Add terms and conditions from quotation data"""
        # Always start Terms & Conditions on a new page
        self.elements.append(PageBreak())
        
        self.elements.append(Paragraph("Terms & Conditions", self.styles['SectionHeader']))
        self.elements.append(Spacer(1, 10))
        
        # Get terms and conditions from the quotation
        terms_conditions = self.quotation.terms_conditions.all()
        
        if terms_conditions:
            # Group terms by type
            payment_terms = []
            delivery_terms = []
            other_terms = []
            
            for term in terms_conditions:
                term_type_name = term.terms_condition_type.name.lower()
                if 'payment' in term_type_name:
                    payment_terms.append(term.terms)
                elif 'delivery' in term_type_name:
                    delivery_terms.append(term.terms)
                else:
                    other_terms.append(term.terms)
            
            # Add Payment Terms section
            if payment_terms:
                self.elements.append(Paragraph("<b>PAYMENT TERMS:</b>", self.styles['SubHeader']))
                for idx, term in enumerate(payment_terms, 1):
                    self.elements.append(Paragraph(f"{idx}. {term}", self.styles['Value']))
                self.elements.append(Spacer(1, 8))
            
            # Add Delivery Terms section
            if delivery_terms:
                self.elements.append(Paragraph("<b>DELIVERY TERMS:</b>", self.styles['SubHeader']))
                for idx, term in enumerate(delivery_terms, 1):
                    self.elements.append(Paragraph(f"{idx}. {term}", self.styles['Value']))
                self.elements.append(Spacer(1, 8))
            
            # Add Other Terms section
            if other_terms:
                self.elements.append(Paragraph("<b>GENERAL TERMS:</b>", self.styles['SubHeader']))
                for idx, term in enumerate(other_terms, 1):
                    self.elements.append(Paragraph(f"{idx}. {term}", self.styles['Value']))
                self.elements.append(Spacer(1, 8))
        
        else:
            # Fallback to default terms if no terms are set
            self.elements.append(Paragraph("<b>TAXES:</b> GST will be extra as applicable.", self.styles['Value']))
            self.elements.append(Spacer(1, 5))
            
            self.elements.append(Paragraph("<b>PAYMENT TERMS:</b>", self.styles['SubHeader']))
            default_payment_terms = [
                "For HVAC Equipment: 100% advance along with PO against Performa Invoice.",
                "Purchase Order and Cheque shall be made in the name of KRISNA AIRCONDITIONING, Pune.",
                "Bank of India, Account Number: 051520100000616, IFSC Code: BKID0000515, GSTIN: 27AITPP8825B2ZS."
            ]
            for idx, term in enumerate(default_payment_terms, 1):
                self.elements.append(Paragraph(f"{idx}. {term}", self.styles['Value']))
            self.elements.append(Spacer(1, 8))
            
            self.elements.append(Paragraph("<b>DELIVERY TERMS:</b>", self.styles['SubHeader']))
            default_delivery_terms = [
                "Delivery will be made within 15-20 working days from the date of receipt of order.",
                "Material will be delivered at site during working hours only."
            ]
            for idx, term in enumerate(default_delivery_terms, 1):
                self.elements.append(Paragraph(f"{idx}. {term}", self.styles['Value']))
            self.elements.append(Spacer(1, 8))
        
        # Add standard closing text
        closing_text = [
            "We hope we are in line with your requirement and look forward to hear from you with interest.",
            "",
            "Thanking you and assuring you our best of services always."
        ]
        
        for text in closing_text:
            if text == "":
                self.elements.append(Spacer(1, 5))
            else:
                self.elements.append(Paragraph(text, self.styles['Value']))
        
        self.elements.append(Spacer(1, 10))

    def add_footer(self):
        """Add footer with signature"""
        data = [
            [
                Paragraph("<b>For Krisna Airconditioning</b>", self.styles['Value']),
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
            ('LINEABOVE', (0, 1), (-1, 1), 1, colors.black),
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
    generator = QuotationPDFGenerator(quotation, version)
    return generator.generate()
