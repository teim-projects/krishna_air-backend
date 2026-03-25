# quotation/utils/pdf_generator.py
# Updated: 2026-03-10 - Match exact format from screenshots

import io
import logging
import os
from datetime import datetime
from decimal import Decimal
from PIL.Image import item
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from django.http import HttpResponse
from django.conf import settings
from collections import defaultdict
from reportlab.platypus import KeepTogether
# from rich.pretty import data
# from rich.pretty import data
# from rich.pretty import data





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
            topMargin=30*mm,
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
            alignment=TA_LEFT,   # ✅ CHANGE THIS
            spaceBefore=2,
            spaceAfter=1 
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
        
    def draw_company_header(self, canvas, doc, quotation):
        canvas.saveState()

        # Logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'ka-logo.png')
        if os.path.exists(logo_path):
            canvas.drawImage(
                logo_path,
                40,
                780,
                width=60,
                height=40,
                mask='auto'   # 👈 IMPORTANT
                )

        # Company details
        if quotation.branch:
            branch = quotation.branch
            company_name = branch.name
            address = f"{branch.address}, {branch.city}, {branch.state} - {branch.pincode}"
            email = branch.email
        else:
            company_name = "KRISNA AIR CONDITIONING"
            address = "309/B, Patil Plaza, Pune - 411009"
            email = "sales@krisnatech.com"

        # Right side text
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(550, 800, company_name)

        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(550, 785, address)
        canvas.drawRightString(550, 770, f"Email: {email}")

        canvas.restoreState()
     
    def add_quotation_title(self): 
        # Get site information
        site_info = ""
        if self.quotation.site:
            site_info = f"{self.quotation.site.name} - {self.quotation.site.address}, {self.quotation.site.city}"
        elif self.quotation.site_name:
            site_info = self.quotation.site_name
        
        # To, Subject section
        customer = self.quotation.customer

        customer_name = customer.name if customer else ""
        customer_contact = customer.contact_number if customer else ""
        customer_email = getattr(customer, "email", "")
        
        customer_address = ""
        if hasattr(customer, "address") and customer.address:
            customer_address = customer.address
        
        # Format date
        quotation_date = self.quotation.created_at.strftime("%d-%m-%Y") if self.quotation.created_at else datetime.now().strftime("%d-%m-%Y")
        quotation_no = self.version.version_no or self.quotation.quotation_no
        data = [
            [
                Paragraph(f'<u><b>To,</b></u> <br /> <b>{customer_name}</b>', self.styles['Value']),
                Paragraph(f'<b>Date:</b> {quotation_date}', self.styles['Value'])
            ],
            [
                Paragraph(f'{customer_address}', self.styles['Value']),
                Paragraph(f'<b>Quotation No:</b> {quotation_no}', self.styles['Value'])
            ],
            [
                Paragraph(f'Contact: {customer_contact}', self.styles['Value']),
                ''
            ],
            [
                Paragraph(f'Email: {customer_email}', self.styles['Value']),
                ''
            ],
            [
                Paragraph(f'<u><b>Subject:</b></u> {self.quotation.subject}', self.styles['UnderlinedLabel']),
                ''
            ],
        ]
        table = Table(data, colWidths=[self.doc.width * 0.7, self.doc.width * 0.3])
        # table = Table(data, colWidths=[self.doc.width, 0])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 5))
        
        # Site Name section (if site information exists)
        if site_info:
            self.elements.append(Paragraph(f'<u><b>Site Name:</b></u> {site_info}', self.styles['UnderlinedLabel']))
            self.elements.append(Spacer(1, 5))
        
        # Greeting
        self.elements.append(Paragraph('Dear Sir/Madam,', self.styles['Value']))
        self.elements.append(Spacer(1, 5))
        
        # Introduction text - only use thank_you_note if available
        if self.quotation.thank_you_note:
            intro_text = self.quotation.thank_you_note
            self.elements.append(Paragraph(intro_text, self.styles['Value']))
            self.elements.append(Spacer(1, 2))

    def add_high_side_items(self):
        """Add high side items grouped by product"""
        try:
            high_items = self.version.high_side_items.all()
            if not high_items:
                return
    
            from collections import defaultdict
            grouped_items = defaultdict(list)
    
            # Group items by brand
            for item in high_items:
                variant = item.product_variant
                model = variant.product_model if hasattr(variant, "product_model") else None
                brand_name = model.brand_id.name if model and model.brand_id else "Unknown"
                grouped_items[brand_name].append(item)
    
            # Loop brand-wise
            for brand_name, items in grouped_items.items():
            
                # Header
                header_table = Table(
                    [[Paragraph(f"Supply of {brand_name} Airconditioners", self.styles["SubHeader"])]],
                    colWidths=[self.doc.width - 10]
                )
    
                header_table.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),
                    ('LEFTPADDING', (0, 0), (-1, -1), self.doc.width/2 - 80),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
    
                self.elements.append(header_table)
    
                # Table Data
                data = [['S.N', 'Description', 'Unit', 'Qty', 'Rate', 'Amount']]
    
                subtotal = 0
                gst_total = 0
                mathadi_charges = 0
                transportation = 0
                grand_total = 0
                total = 0
                
                for idx, item in enumerate(items, 1):
                    variant = item.product_variant
                    model = variant.product_model
                
                    description = f"{model.name} {model.model_no} {variant.capacity}"
                
                    qty = float(item.quantity)
                    rate = float(item.unit_price)
                
                    # ✅ USE DB VALUES
                    base_amount = float(getattr(item, "base_amount", 0) or 0)
                    gst_amount = float(getattr(item, "gst_amount", 0) or 0)
                    total_amount = float(getattr(item, "total_with_gst", 0) or 0)
                
                    # ✅ accumulate
                    subtotal += base_amount
                    gst_total += gst_amount
                    grand_total += total_amount
                
                    mathadi_charges += float(getattr(item, "mathadi_charges", 0) or 0)
                    transportation += float(getattr(item, "transportation_charges", 0) or 0)
                    total += float(getattr(item, "total_with_gst", 0) or 0)
                    data.append([
                        str(idx),
                        Paragraph(description, self.styles['Value']),
                        "Nos.",
                        str(item.quantity),
                        f"{rate:,.2f}",
                        f"{base_amount:,.2f}",   # 👈 show base amount
                    ])
                # Calculations
                gst = subtotal * 0.18
                total = total
    
                # Format helper
                def format_extra(value):
                    return f"{value:,.2f}" if value > 0 else "Extra"
    
                # Totals rows
                data.append(['', '', '', '', 'Sub Total :', f"{subtotal:,.2f}"])
                data.append(['', '', '', '', 'GST @ 18% :', f"{gst:,.2f}"])
                data.append(['', '', '', '', 'Mathadi Charges :', format_extra(mathadi_charges)])
                data.append(['', '', '', '', 'Transportation :', format_extra(transportation)])
                data.append(['', '', '', '', 'Total :', f"{total:,.2f}"])
    
                # Column widths
                total_width = self.doc.width
                col_widths = [
                    total_width * 0.05,
                    total_width * 0.43,
                    total_width * 0.10,
                    total_width * 0.08,
                    total_width * 0.16,
                    total_width * 0.16,
                ]
    
                table = Table(data, colWidths=col_widths)
    
                # Table Styling
                table.setStyle(TableStyle([
                    # Grid only for items
                    ('GRID', (0, 0), (-1, -6), 0.5, colors.black),
    
                    # Horizontal lines for totals
                    ('LINEABOVE', (0, -5), (-1, -5), 0.5, colors.black),
                    ('LINEBELOW', (0, -5), (-1, -1), 0.5, colors.black),
                    ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
    
                    # Only one vertical divider (label | value)
                    ('LINEBEFORE', (5, -5), (5, -1), 0.5, colors.black),
    
                    # Fonts & alignment
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
    
                    # Span totals
                    ('SPAN', (0, -5), (3, -5)),
                    ('SPAN', (0, -4), (3, -4)),
                    ('SPAN', (0, -3), (3, -3)),
                    ('SPAN', (0, -2), (3, -2)),
                    ('SPAN', (0, -1), (3, -1)),
    
                    ('ALIGN', (4, -5), (4, -1), 'RIGHT'),
                    ('ALIGN', (5, -5), (5, -1), 'RIGHT'),
                    ('FONTNAME', (4, -5), (-1, -1), 'Helvetica-Bold'),
    
                    # Highlight total row
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#8bc34a")),
                ]))
    
                self.elements.append(table)
                self.elements.append(Spacer(1, 10))
    
        except Exception as e:
            logger.error(f"Error in add_high_side_items: {str(e)}")    
                
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

            total_width = self.doc.width-20

            col_widths = [
                total_width * 0.05,
                total_width * 0.45,
                total_width * 0.10,
                total_width * 0.08,
                total_width * 0.16,
                total_width * 0.16,
            ]
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
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),

                # Extra spacing for description column (important)
                ('LEFTPADDING', (1, 0), (1, -1), 6),
                ('RIGHTPADDING', (1, 0), (1, -1), 6),
                
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
                self.elements.append(Spacer(1, 5))
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
        self.elements.append(Spacer(1, 5))
        
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
        
        self.elements.append(Spacer(1, 5))

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
    # def generate(self):
        
    #     self.add_quotation_title()
    #     self.add_customer_details()
    
    #     has_high = self.version.high_side_items.exists()
    #     has_low = self.version.low_side_items.exists()
    
    #     if has_high:
    #         self.add_high_side_items()
    
    #     # 👇 IMPORTANT LOGIC
    #     if has_high and has_low:
    #         self.elements.append(PageBreak())
    
    #     if has_low:
    #         self.add_low_side_items()
    
    #     self.add_tax_summary()
    #     self.add_terms_and_conditions()
    #     self.add_footer()
    #     self.doc.build(
    #         self.elements,
    #         onFirstPage=lambda c, d: self.draw_company_header(c, d, self.quotation),
    #         onLaterPages=lambda c, d: self.draw_company_header(c, d, self.quotation),
    #     )
    
    #     pdf = self.buffer.getvalue()
    #     self.buffer.close()
    #     return pdf
    def generate(self):
        top_elements = []

        # Step 1: collect top content
        self.elements = top_elements
        self.add_quotation_title()

        has_high = self.version.high_side_items.exists()
        has_low = self.version.low_side_items.exists()

        if has_high:
            self.add_high_side_items()

        # ✅ Step 2: Create container PROPERLY
        container = Table(
            [[elem] for elem in top_elements],   # split rows
            colWidths=[self.doc.width]
        )

        container.setStyle(TableStyle([
            # ('BOX', (0, 0), (-1, -1), 1, colors.black),

            # 🔥 reduce padding (IMPORTANT)
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),

            # 🔥 REMOVE extra row spacing
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Step 3: reset elements
        self.elements = [container]

        # Step 4: continue rest
        if has_high and has_low:
            self.elements.append(PageBreak())

        if has_low:
            self.add_low_side_items()

        self.add_tax_summary()
        self.add_terms_and_conditions()
        self.add_footer()

        # Step 5: build
        self.doc.build(
            self.elements,
            onFirstPage=lambda c, d: self.draw_company_header(c, d, self.quotation),
            onLaterPages=lambda c, d: self.draw_company_header(c, d, self.quotation),
        )

        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf
    
def generate_quotation_pdf(quotation, version):
    """Generate PDF for quotation"""
    generator = QuotationPDFGenerator(quotation, version)
    return generator.generate()
