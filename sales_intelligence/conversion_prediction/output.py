"""Reusable Lead Conversion Prediction Output Builder.

This module is CRM-independent.

It converts model predictions into a standardized
Sales Intelligence output structure.
"""


def classify_conversion_probability(probability):
    """
    Classify conversion probability into a business category.

    Development thresholds:

        >= 0.70 -> High
        >= 0.40 -> Medium
        < 0.40  -> Low

    These thresholds are development/business-rule
    thresholds only.

    They are not statistically validated production
    thresholds because the current model is trained
    using synthetic development data.
    """

    if probability >= 0.70:
        return "High"

    elif probability >= 0.40:
        return "Medium"

    else:
        return "Low"


def build_conversion_output(
    feature_records,
    probabilities,
    predictions,
):
    """
    Build standardized conversion prediction output.

    Parameters
    ----------
    feature_records : list[dict]
        Universal lead feature records.

    probabilities : list[float]
        Predicted conversion probabilities.

    predictions : list[int]
        Predicted conversion classifications.

    Returns
    -------
    list[dict]
        Standardized conversion prediction records.
    """

    if len(feature_records) != len(probabilities):
        raise ValueError(
            "Number of feature records must match "
            "number of probabilities."
        )

    if len(feature_records) != len(predictions):
        raise ValueError(
            "Number of feature records must match "
            "number of predictions."
        )

    output = []

    for index, record in enumerate(
        feature_records
    ):
        probability = float(
            probabilities[index]
        )

        output.append(
            {
                "lead_id": record.get(
                    "lead_id"
                ),
                "conversion_probability": round(
                    probability,
                    4,
                ),
                "conversion_prediction": int(
                    predictions[index]
                ),
                "conversion_class": classify_conversion_probability(
                    probability
                ),
            }
        )

    return output

