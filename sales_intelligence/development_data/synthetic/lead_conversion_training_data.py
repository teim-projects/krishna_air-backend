"""
Synthetic Lead Conversion Training Data.

IMPORTANT
---------
This dataset is fabricated development data.

It is generated using feature patterns observed in the
Krishna CRM, but it is NOT copied from actual customers
and does NOT represent actual historical outcomes.

Purpose:
- Develop the Lead Conversion Prediction algorithm
- Create enough labeled data for model evaluation
- Prototype the reusable Logistic Regression model
"""

import random


random.seed(42)


SOURCES = [
    "reference",
    "existing_customer",
    "bni",
    "scgt",
    "indiamart",
    "architect/interior_designer",
    "google_ads",
    "justdial",
    "other",
]

LEAD_TYPES = [
    "individual",
    "organization",
]

SOURCE_QUALITY_MAP = {
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


def calculate_conversion_tendency(
    source_quality,
    stage_strength,
    followup_count,
    engagement_level,
    has_quotation,
    quote_value,
    is_qualified,
    is_service_lead,
    lead_age_days,
    activity_age_days,
):
    """
    Generate a synthetic conversion tendency.

    This is a fabricated business rule used only to
    create development labels.

    It is NOT a trained model and does not represent
    actual historical Krishna conversion behavior.
    """

    score = 0

    # -------------------------------------------------
    # SOURCE QUALITY
    # -------------------------------------------------

    score += source_quality * 15

    # -------------------------------------------------
    # LEAD STAGE
    # -------------------------------------------------

    score += stage_strength * 20

    # -------------------------------------------------
    # FOLLOW-UP ACTIVITY
    # -------------------------------------------------

    if followup_count >= 3:
        score += 15

    elif followup_count == 2:
        score += 10

    elif followup_count == 1:
        score += 5

    # -------------------------------------------------
    # ENGAGEMENT
    # -------------------------------------------------

    score += engagement_level * 15

    # -------------------------------------------------
    # QUOTATION
    # -------------------------------------------------

    if has_quotation:
        score += 10

    # -------------------------------------------------
    # QUOTATION VALUE
    # -------------------------------------------------

    if quote_value > 50000:
        score += 15

    elif quote_value > 10000:
        score += 10

    elif quote_value > 0:
        score += 5

    # -------------------------------------------------
    # QUALIFICATION
    # -------------------------------------------------

    if is_qualified:
        score += 10

    # -------------------------------------------------
    # SERVICE LEAD
    # -------------------------------------------------

    if is_service_lead:
        score -= 2

    # -------------------------------------------------
    # RECENCY
    # -------------------------------------------------

    if activity_age_days <= 30:
        score += 5

    elif activity_age_days <= 60:
        score += 2

    # -------------------------------------------------
    # LEAD AGE
    # -------------------------------------------------

    if lead_age_days <= 60:
        score += 2

    # -------------------------------------------------
    # CONTROLLED RANDOMNESS
    # -------------------------------------------------

    score += random.randint(
        -8,
        8,
    )

    return score


def generate_record(index):
    """
    Generate one synthetic lead conversion record.

    Feature distributions are intentionally based on
    patterns observed in the Krishna CRM.
    """

    # -------------------------------------------------
    # SOURCE
    # -------------------------------------------------

    source = random.choices(
        SOURCES,
        weights=[
            15,  # reference
            8,   # existing_customer
            15,  # bni
            5,   # scgt
            5,   # indiamart
            15,  # architect/interior_designer
            10,  # google_ads
            7,   # justdial
            20,  # other
        ],
        k=1,
    )[0]

    source_quality = SOURCE_QUALITY_MAP[
        source
    ]

    # -------------------------------------------------
    # STAGE
    # -------------------------------------------------

    stage = random.choices(
        [
            "open",
            "in_process",
            "closed",
        ],
        weights=[
            75,
            10,
            15,
        ],
        k=1,
    )[0]

    stage_strength_map = {
        "open": 0.6,
        "in_process": 1.0,
        "closed": 0.0,
    }

    stage_strength = stage_strength_map[
        stage
    ]

    # -------------------------------------------------
    # FOLLOW-UP ACTIVITY
    # -------------------------------------------------

    followup_count = random.choices(
        [
            0,
            1,
            2,
            3,
            4,
            5,
        ],
        weights=[
            65,
            18,
            9,
            4,
            2,
            2,
        ],
        k=1,
    )[0]

    if followup_count >= 3:
        engagement_level = 1.0

    elif followup_count == 2:
        engagement_level = 0.7

    elif followup_count == 1:
        engagement_level = 0.4

    else:
        engagement_level = 0.0

    # -------------------------------------------------
    # QUOTATION
    # -------------------------------------------------

    has_quotation = random.choices(
        [
            0,
            1,
        ],
        weights=[
            85,
            15,
        ],
        k=1,
    )[0]

    if has_quotation:

        quote_value = random.choice(
            [
                659,
                2500,
                5000,
                8500,
                12000,
                18000,
                29024,
                34068.32,
                50000,
                75000,
                100000,
                150000,
                194523,
                218523,
                222843,
            ]
        )

    else:
        quote_value = 0.0

    # -------------------------------------------------
    # QUALIFICATION
    # -------------------------------------------------

    is_qualified = random.choices(
        [
            0,
            1,
        ],
        weights=[
            75,
            25,
        ],
        k=1,
    )[0]

    # -------------------------------------------------
    # LEAD TYPE
    # -------------------------------------------------

    lead_type = random.choices(
        [
            "individual",
            "organization",
        ],
        weights=[
            80,
            20,
        ],
        k=1,
    )[0]

    # -------------------------------------------------
    # SERVICE / SALES
    # -------------------------------------------------

    is_service_lead = random.choices(
        [
            1,
            0,
        ],
        weights=[
            85,
            15,
        ],
        k=1,
    )[0]

    # -------------------------------------------------
    # LEAD AGE
    # -------------------------------------------------

    lead_age_days = random.randint(
        40,
        210,
    )

    # -------------------------------------------------
    # ACTIVITY AGE
    # -------------------------------------------------

    activity_age_days = random.randint(
        40,
        min(
            lead_age_days,
            210,
        ),
    )

    # -------------------------------------------------
    # SYNTHETIC CONVERSION TENDENCY
    # -------------------------------------------------

    score = calculate_conversion_tendency(
        source_quality=source_quality,
        stage_strength=stage_strength,
        followup_count=followup_count,
        engagement_level=engagement_level,
        has_quotation=has_quotation,
        quote_value=quote_value,
        is_qualified=is_qualified,
        is_service_lead=is_service_lead,
        lead_age_days=lead_age_days,
        activity_age_days=activity_age_days,
    )

    # -------------------------------------------------
    # SYNTHETIC TARGET
    # -------------------------------------------------
    #
    # The threshold is intentionally lower than the
    # previous version because the Krishna-like
    # feature distribution produces lower scores.
    #
    # This creates a more useful development class
    # balance for Logistic Regression.
    #
    # These labels are fabricated and are NOT actual
    # Krishna CRM conversion outcomes.
    # -------------------------------------------------

    conversion_threshold = random.randint(
        35,
        50,
    )

    converted = (
        1
        if score >= conversion_threshold
        else 0
    )

    return {
        "source_quality": source_quality,
        "stage_strength": stage_strength,
        "followup_count": followup_count,
        "engagement_level": engagement_level,
        "lead_age_days": lead_age_days,
        "activity_age_days": activity_age_days,
        "has_quotation": has_quotation,
        "quote_value": quote_value,
        "is_qualified": is_qualified,
        "is_service_lead": is_service_lead,
        "lead_type": lead_type,
        "converted": converted,
    }


# -----------------------------------------------------
# SYNTHETIC DEVELOPMENT DATASET
# -----------------------------------------------------

SYNTHETIC_LEAD_CONVERSION_DATA = [
    generate_record(index)
    for index in range(500)
]

