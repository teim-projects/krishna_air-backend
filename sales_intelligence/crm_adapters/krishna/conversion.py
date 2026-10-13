"""
Krishna CRM Conversion Adapter.

Determines actual lead conversion outcomes from Krishna CRM data.

CRM-specific logic belongs here.
The reusable conversion prediction module must not import
Krishna CRM models directly.
"""

from invoice.models import Invoice
from lead_management.models import lead_management


def get_krishna_conversion_outcomes():
    """
    Build universal conversion outcomes from Krishna invoices.

    A lead is considered converted when an invoice can be
    attributed to that lead.

    If multiple leads belong to the same customer, the invoice
    is attributed to the latest lead created on or before the
    invoice date.

    Returns
    -------
    list[dict]
        Universal conversion outcome records.
    """

    outcomes = {}

    leads = lead_management.objects.select_related(
        "customer"
    ).all()

    for invoice in Invoice.objects.all():

        if not invoice.customer:
            continue

        customer_leads = [
            lead
            for lead in leads
            if lead.customer_id == invoice.customer_id
            and lead.date is not None
            and invoice.invoice_date is not None
            and lead.date <= invoice.invoice_date
        ]

        if not customer_leads:
            continue

        # Select the latest lead before the invoice.
        matched_lead = max(
            customer_leads,
            key=lambda lead: lead.date
        )

        outcomes[matched_lead.id] = {
            "lead_id": matched_lead.id,
            "converted": True,
        }

    return list(outcomes.values())
