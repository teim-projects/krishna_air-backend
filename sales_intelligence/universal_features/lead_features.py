"""
Universal Lead Feature Standard.

This defines the common lead features expected by
the reusable Sales Intelligence algorithms.

CRM-specific field names and values must be converted
to these standard features by the CRM adapter.
"""


UNIVERSAL_LEAD_FEATURES = [
    "lead_id",
    "source_quality",
    "stage_strength",
    "followup_count",
    "engagement_level",
    "has_quotation",
    "quote_value",
    "activity_age_days",
]