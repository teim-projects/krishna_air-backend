"""
Krishna CRM Lead Adapter.

Converts Krishna CRM data into the universal lead
feature format used by Sales Intelligence.

This module contains CRM-specific mappings only.
Reusable algorithms must not depend on Krishna models.
"""

from django.utils import timezone

from lead_management.models import lead_management
from lead_management.models import LeadFollowUp


def get_source_quality(source):
    """
    Convert Krishna CRM lead source into a normalized
    source-quality value between 0 and 1.
    """

    source = (source or "").strip().lower()

    source_quality = {
        "reference": 1.0,
        "existing_customer": 1.0,
        "bni": 0.8,
        "scgt": 0.7,
        "indiamart": 0.7,
        "architect/interior_designer": 0.7,
        "google_ads": 0.6,
        "justdial": 0.6,
        "other": 0.5,
    }

    return source_quality.get(source, 0.5)


def get_stage_strength(status):
    """
    Convert Krishna CRM lead status into normalized
    stage strength.
    """

    status = (status or "").strip().lower()

    stage_strength = {
        "in_process": 1.0,
        "open": 0.6,
        "closed": 0.0,
    }

    return stage_strength.get(status, 0.5)


def get_engagement_level(followup_count):
    """
    Convert follow-up activity into normalized engagement.
    """

    if followup_count >= 3:
        return 1.0

    if followup_count == 2:
        return 0.7

    if followup_count == 1:
        return 0.4

    return 0.0


def get_krishna_lead_features():
    """
    Extract Krishna CRM leads and convert them into
    the universal lead feature format.

    This adapter is CRM-specific.
    The returned feature format is CRM-independent.
    """

    today = timezone.localdate()

    feature_records = []

    for lead in lead_management.objects.all():

        followup_count = LeadFollowUp.objects.filter(
            lead_id=lead.id
        ).count()

        quote_exists = lead.customer.quotations.exists()

        quote_value = 0

        if quote_exists:
            active_quotations = lead.customer.quotations.all()

            for quotation in active_quotations:
                active_version = quotation.versions.filter(
                    is_active=True
                ).first()

                if active_version:
                    quote_value += active_version.grand_total or 0

        lead_date = lead.date or lead.enquiry_date

        lead_age_days = (
            (today - lead_date).days
            if lead_date
            else None
        )

        activity_date = (
            lead.followup_date
            or lead.enquiry_date
            or lead.date
        )

        activity_age_days = (
            (today - activity_date).days
            if activity_date
            else None
        )

        feature_records.append({
            "lead_id": lead.id,

            "customer": (
                lead.customer.name
                if lead.customer
                else "-"
            ),

            # Existing Week 1-2 features
            "source_quality": get_source_quality(
                lead.lead_source
            ),

            "stage_strength": get_stage_strength(
                lead.status
            ),

            "followup_count": followup_count,

            "engagement_level": get_engagement_level(
                followup_count
            ),

            "has_quotation": quote_exists,

            "quote_value": float(quote_value),

            "activity_age_days": activity_age_days,

            # Week 3 features
            "lead_age_days": lead_age_days,

            "is_qualified": bool(
                lead.is_qualified
            ),

            "is_service_lead": bool(
                lead.is_service_lead
            ),

            "lead_type": lead.lead_type or "",
        })

    return feature_records
