"""
Reusable Lead Conversion Prediction Feature Builder.

This module is CRM-independent.

It accepts universal lead feature records and prepares
the features required by the conversion prediction model.

The lead_id is preserved so that predictions can be
mapped back to the original CRM lead.
"""

CONVERSION_FEATURES = [
    "source_quality",
    "stage_strength",
    "followup_count",
    "engagement_level",
    "lead_age_days",
    "activity_age_days",
    "has_quotation",
    "quote_value",
    "is_qualified",
    "is_service_lead",
    "lead_type",
]


def build_conversion_features(feature_records):
    """
    Prepare universal features for the conversion model.

    The lead_id is preserved as an identifier but is not
    used as a model feature.
    """

    prepared_records = []

    for record in feature_records:
        prepared_record = {
            feature: record.get(feature)
            for feature in CONVERSION_FEATURES
        }

        prepared_record["lead_id"] = record.get(
            "lead_id"
        )

        prepared_records.append(
            prepared_record
        )

    return prepared_records