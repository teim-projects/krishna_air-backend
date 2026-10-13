"""
Reusable Lead Conversion Prediction Pipeline.

This module is CRM-independent.

It provides reusable functions for:

1. Training a conversion model
2. Predicting conversion probability
3. Building standardized conversion output

CRM-specific data extraction must happen outside
this module through CRM adapters.
"""

from .feature_builder import build_conversion_features
from .target_builder import build_conversion_target
from .model import (
    train_conversion_model,
    predict_conversion_probability,
    predict_conversion,
)
from .output import build_conversion_output


def train_conversion_pipeline(
    feature_records,
    outcome_records,
):
    """
    Train the reusable lead conversion model.

    Parameters
    ----------
    feature_records : list[dict]
        Universal training feature records.

    outcome_records : list[dict]
        Universal training outcome records.

        Each record must contain:
            converted: True / False

    Returns
    -------
    model
        Trained conversion prediction model.
    """

    if not feature_records:
        raise ValueError(
            "Feature records cannot be empty."
        )

    if not outcome_records:
        raise ValueError(
            "Outcome records cannot be empty."
        )

    prepared_features = build_conversion_features(
        feature_records
    )

    targets = build_conversion_target(
        outcome_records
    )

    if len(prepared_features) != len(targets):
        raise ValueError(
            "Number of feature records must match "
            "number of outcome records."
        )

    model = train_conversion_model(
        prepared_features,
        targets,
    )

    return model


def predict_conversion_pipeline(
    model,
    feature_records,
):
    """
    Generate standardized conversion predictions.

    Parameters
    ----------
    model
        Trained conversion prediction model.

    feature_records : list[dict]
        Universal CRM feature records.

    Returns
    -------
    list[dict]
        Standardized conversion predictions.
    """

    if not feature_records:
        return []

    prepared_features = build_conversion_features(
        feature_records
    )

    probabilities = predict_conversion_probability(
        model,
        prepared_features,
    )

    predictions = predict_conversion(
        model,
        prepared_features,
    )

    outputs = build_conversion_output(
        prepared_features,
        probabilities,
        predictions,
    )

    return outputs