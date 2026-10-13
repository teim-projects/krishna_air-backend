"""
Reusable Enhanced Lead Scoring Rules.

This module is CRM-independent.

It accepts only universal lead features and does not
contain CRM-specific source names, field names, or
database logic.
"""


def get_source_score(source_quality):
    """
    Convert normalized source quality (0-1)
    into a maximum of 15 points.
    """

    source_quality = max(0, min(1, source_quality or 0))

    return round(source_quality * 15)


def get_stage_score(stage_strength):
    """
    Convert normalized stage strength (0-1)
    into a maximum of 20 points.
    """

    stage_strength = max(0, min(1, stage_strength or 0))

    return round(stage_strength * 20)


def get_followup_score(followup_count):
    """
    Convert follow-up activity into a maximum of 15 points.
    """

    if followup_count >= 3:
        return 15

    if followup_count == 2:
        return 10

    if followup_count == 1:
        return 5

    return 0


def get_engagement_score(engagement_level):
    """
    Convert normalized engagement level (0-1)
    into a maximum of 15 points.
    """

    engagement_level = max(
        0,
        min(1, engagement_level or 0)
    )

    return round(engagement_level * 15)


def get_quotation_score(has_quotation):
    """
    Add points when quotation information is available.
    """

    return 10 if has_quotation else 0


def get_quote_value_score(quote_value):
    """
    Convert quote value into a maximum of 15 points.

    These are configurable initial business rules.
    """

    quote_value = quote_value or 0

    if quote_value > 50000:
        return 15

    if quote_value > 10000:
        return 10

    if quote_value > 0:
        return 5

    return 0


def get_recency_score(activity_age_days):
    """
    Score how recently sales activity occurred.

    Maximum = 10 points.
    """

    if activity_age_days is None:
        return 0

    if activity_age_days <= 7:
        return 10

    if activity_age_days <= 15:
        return 7

    if activity_age_days <= 30:
        return 4

    return 0


def calculate_enhanced_lead_score(features):
    """
    Calculate an enhanced lead score from universal
    lead features.

    Maximum possible score = 100.
    """

    score = 0

    score += get_source_score(
        features.get("source_quality")
    )

    score += get_stage_score(
        features.get("stage_strength")
    )

    score += get_followup_score(
        features.get("followup_count", 0)
    )

    score += get_engagement_score(
        features.get("engagement_level")
    )

    score += get_quotation_score(
        features.get("has_quotation", False)
    )

    score += get_quote_value_score(
        features.get("quote_value", 0)
    )

    score += get_recency_score(
        features.get("activity_age_days")
    )

    return score