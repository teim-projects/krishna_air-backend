"""
Reusable Lead Scoring Engine.

This module works with universal lead features
and is independent of any CRM.
"""

from .scoring_rules import calculate_enhanced_lead_score


def get_lead_priority(score):
    """
    Convert the final lead score into a priority category.
    """

    if score >= 80:
        return "High"

    if score >= 50:
        return "Medium"

    return "Low"


def score_lead(features):
    """
    Score one lead using universal features.
    """

    score = calculate_enhanced_lead_score(features)

    return {
        **features,
        "lead_score": score,
        "priority": get_lead_priority(score),
    }


def score_leads(feature_records):
    """
    Score multiple leads.
    """

    return [
        score_lead(features)
        for features in feature_records
    ]