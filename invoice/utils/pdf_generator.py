# utils/pdf_generator.py
import io
from datetime import datetime
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.http import HttpResponse
from django.conf import settings
import os

class InvoicePDFGenerator:
    def __init__(self, invoice):
        self.invoice = invoice
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=10*mm,
            bottomMargin=10*mm
        )
        self.styles = getSampleStyleSheet()
        self.elements = []
        self.setup_styles()

    def setup_styles(self):
        """Setup custom styles for the PDF"""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_CENTER,
            spaceAfter=2,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Normal'],
            fontSize=24,
            textColor=colors.HexColor('#E74C3C'),
            alignment=TA_CENTER,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='Address',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=TA_CENTER,
            leading=12
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2C3E50'),
            fontName='Helvetica-Bold',
            spaceBefore=10,
            spaceAfter=5
        ))

        self.styles.add(ParagraphStyle(
            name='Label',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#7F8C8D'),
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='Value',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#2C3E50'),
            leading=14
        ))

    def add_company_header(self):
        """Add company header section"""
        data = [
            [Paragraph(self.invoice.company_name.upper(), self.styles['CompanyName'])],
            [Paragraph(self.invoice.company_address.replace('\n', '<br/>'), self.styles['Address'])],
            [Paragraph(f"GSTIN: {self.invoice.company_gstin} | PAN: {self.invoice.company_pan}", self.styles['Address'])],
            [Paragraph(f"MSME: {self.invoice.company_msme_number or 'N/A'} | Email: {self.invoice.company_email or 'N/A'}", self.styles['Address'])],
        ]
        
        table = Table(data, colWidths=[self.doc.width])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#E74C3C')),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_invoice_title(self):
        """Add invoice title and basic info"""
        # Title
        self.elements.append(Paragraph("TAX INVOICE", self.styles['InvoiceTitle']))
        
        # Invoice details in two columns
        data = [
            [
                Paragraph(f"<b>Invoice No:</b> {self.invoice.invoice_no}", self.styles['Value']),
                Paragraph(f"<b>Date:</b> {self.invoice.invoice_date.strftime('%d-%m-%Y')}", self.styles['Value'])
            ],
            [
                Paragraph(f"<b>Supplier Ref:</b> {self.invoice.supplier_ref or 'N/A'}", self.styles['Value']),
                Paragraph(f"<b>Buyer Order No:</b> {self.invoice.buyer_order_no or 'N/A'}", self.styles['Value'])
            ]
        ]
        
        table = Table(data, colWidths=[self.doc.width/2.0 - 10, self.doc.width/2.0 - 10])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_buyer_details(self):
        """Add buyer and shipping details"""
        self.elements.append(Paragraph("Buyer Details", self.styles['SectionHeader']))
        
        data = [
            [
                Paragraph("<b>Buyer:</b>", self.styles['Label']),
                Paragraph(self.invoice.buyer_name, self.styles['Value'])
            ],
            [
                Paragraph("<b>Address:</b>", self.styles['Label']),
                Paragraph(self.invoice.buyer_address.replace('\n', '<br/>'), self.styles['Value'])
            ],
            [
                Paragraph("<b>GSTIN:</b>", self.styles['Label']),
                Paragraph(self.invoice.buyer_gstin or 'N/A', self.styles['Value'])
            ],
            [
                Paragraph("<b>State:</b>", self.styles['Label']),
                Paragraph(f"{self.invoice.buyer_state or 'N/A'} (Code: {self.invoice.buyer_state_code or 'N/A'})", self.styles['Value'])
            ]
        ]
        
        if self.invoice.ship_to_address:
            data.append([
                Paragraph("<b>Ship To:</b>", self.styles['Label']),
                Paragraph(self.invoice.ship_to_address.replace('\n', '<br/>'), self.styles['Value'])
            ])
        
        table = Table(data, colWidths=[60, self.doc.width - 80])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_items_table(self):
        """Add items table"""
        self.elements.append(Paragraph("Items Details", self.styles['SectionHeader']))
        
        # Table headers
        headers = [
            ['Sr.', 'Description of Goods/Services', 'HSN/SAC', 'Qty', 'Unit', 'Rate (₹)', 'GST%', 'Amount (₹)']
        ]
        
        # Table data
        data = headers.copy()
        for idx, item in enumerate(self.invoice.items.all(), 1):
            data.append([
                str(idx),
                Paragraph(item.description[:50] + ('...' if len(item.description) > 50 else ''), self.styles['Value']),
                item.hsn_sac,
                str(item.quantity),
                item.unit,
                f"{item.rate:,.2f}",
                f"{item.gst_percent}%",
                f"{item.amount:,.2f}"
            ])
        
        # Totals row
        data.append([
            '', '', '', '', '', '', 
            Paragraph("<b>Total:</b>", self.styles['Value']),
            Paragraph(f"<b>₹{self.invoice.taxable_value:,.2f}</b>", self.styles['Value'])
        ])
        
        col_widths = [25, 200, 60, 40, 40, 60, 45, 70]
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (7, 0), (7, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F8F9F9')),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#BDC3C7')),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#2C3E50')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ECF0F1')),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_tax_summary(self):
        """Add tax summary section"""
        self.elements.append(Paragraph("Tax Summary", self.styles['SectionHeader']))
        
        if self.invoice.gst_type == "CGST_SGST":
            data = [
                ['Taxable Value', 'CGST Rate', 'CGST Amount', 'SGST Rate', 'SGST Amount', 'Total Tax'],
                [
                    f"₹{self.invoice.taxable_value:,.2f}",
                    f"9%",
                    f"₹{self.invoice.cgst_amount:,.2f}",
                    f"9%",
                    f"₹{self.invoice.sgst_amount:,.2f}",
                    f"₹{self.invoice.total_tax:,.2f}"
                ]
            ]
        else:
            data = [
                ['Taxable Value', 'IGST Rate', 'IGST Amount', 'Total Tax'],
                [
                    f"₹{self.invoice.taxable_value:,.2f}",
                    f"18%",
                    f"₹{self.invoice.igst_amount:,.2f}",
                    f"₹{self.invoice.total_tax:,.2f}"
                ]
            ]
        
        col_widths = [self.doc.width/len(data[0])] * len(data[0])
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#EBF5FB')),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 5))

    def add_grand_total(self):
        """Add grand total section"""
        data = [
            [
                Paragraph("<b>Grand Total (in words):</b>", self.styles['Value']),
                Paragraph(f"<b>{self.invoice.amount_in_words or ''}</b>", self.styles['Value'])
            ],
            [
                Paragraph("<b>Grand Total (₹):</b>", self.styles['Value']),
                Paragraph(f"<b>₹{self.invoice.grand_total:,.2f}</b>", self.styles['Value'])
            ]
        ]
        
        table = Table(data, colWidths=[120, self.doc.width - 140])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FDEBD0')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E67E22')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_bank_details(self):
        """Add bank details section"""
        data = [
            [Paragraph("<b>Bank Details:</b>", self.styles['Label'])],
            [
                Paragraph(
                    f"Bank: {self.invoice.bank_name}<br/>"
                    f"Account No: {self.invoice.account_no}<br/>"
                    f"IFSC: {self.invoice.ifsc_code}<br/>"
                    f"Branch: {self.invoice.branch}",
                    self.styles['Value']
                )
            ]
        ]
        
        if self.invoice.declaration:
            data.append([Paragraph(f"<b>Declaration:</b> {self.invoice.declaration}", self.styles['Value'])])
        
        table = Table(data, colWidths=[self.doc.width])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F4F6F7')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        self.elements.append(table)
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
                Paragraph("(This is a Computer Generated Invoice)", self.styles['Label'])
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

    def generate(self):
        """Generate the PDF"""
        self.add_company_header()
        self.add_invoice_title()
        self.add_buyer_details()
        self.add_items_table()
        self.add_tax_summary()
        self.add_grand_total()
        self.add_bank_details()
        self.add_footer()
        
        self.doc.build(self.elements)
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf


def generate_invoice_pdf(invoice):
    """Generate PDF for invoice"""
    generator = InvoicePDFGenerator(invoice)
    return generator.generate()