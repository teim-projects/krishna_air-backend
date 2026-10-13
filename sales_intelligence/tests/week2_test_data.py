"""
Synthetic test data for Enhanced Lead Scoring.

This data is used only to test the reusable scoring logic.
It does not represent actual Krishna CRM customers or leads.

All records follow the Universal Lead Feature format.
"""

WEEK2_TEST_LEADS = [
    {
        "lead_id": 101,
        "source_quality": 1.0,
        "stage_strength": 1.0,
        "followup_count": 3,
        "engagement_level": 1.0,
        "has_quotation": True,
        "quote_value": 150000,
        "activity_age_days": 2,
    },
    {
        "lead_id": 102,
        "source_quality": 0.6,
        "stage_strength": 0.6,
        "followup_count": 1,
        "engagement_level": 0.4,
        "has_quotation": False,
        "quote_value": 0,
        "activity_age_days": 10,
    },
    {
        "lead_id": 103,
        "source_quality": 0.5,
        "stage_strength": 0.6,
        "followup_count": 0,
        "engagement_level": 0.0,
        "has_quotation": False,
        "quote_value": 0,
        "activity_age_days": 45,
    },
    {
        "lead_id": 104,
        "source_quality": 1.0,
        "stage_strength": 1.0,
        "followup_count": 2,
        "engagement_level": 0.7,
        "has_quotation": True,
        "quote_value": 34068.32,
        "activity_age_days": 5,
    },
    {
        "lead_id": 105,
        "source_quality": 0.7,
        "stage_strength": 0.0,
        "followup_count": 2,
        "engagement_level": 0.7,
        "has_quotation": True,
        "quote_value": 0,
        "activity_age_days": 20,
    },
]