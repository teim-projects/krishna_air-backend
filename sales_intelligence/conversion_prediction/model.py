"""
Reusable Lead Conversion Prediction Model.

This module is CRM-independent.

It receives prepared feature data and target values.
It does not import CRM models or synthetic datasets.
"""

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERIC_FEATURES = [
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
]

CATEGORICAL_FEATURES = [
    "lead_type",
]


def build_conversion_model():
    """
    Build the reusable Logistic Regression pipeline.

    The model is CRM-independent.
    """

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                StandardScaler(),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000
                ),
            ),
        ]
    )

    return model


def train_conversion_model(
    feature_records,
    targets,
):
    """
    Train the Logistic Regression conversion model.
    """

    if len(feature_records) != len(targets):
        raise ValueError(
            "Number of feature records must match "
            "number of targets."
        )

    if len(feature_records) == 0:
        raise ValueError(
            "Cannot train model with empty feature data."
        )

    if len(set(targets)) < 2:
        raise ValueError(
            "Conversion targets must contain both "
            "converted (1) and non-converted (0) records."
        )

    feature_data = pd.DataFrame(
        feature_records
    )

    model = build_conversion_model()

    model.fit(
        feature_data,
        targets,
    )

    return model


def predict_conversion_probability(
    model,
    feature_records,
):
    """
    Predict conversion probability for each lead.

    Returns probabilities between 0 and 1.
    """

    if not feature_records:
        return []

    feature_data = pd.DataFrame(
        feature_records
    )

    probabilities = model.predict_proba(
        feature_data
    )[:, 1]

    return [
        round(
            float(probability),
            4,
        )
        for probability in probabilities
    ]


def predict_conversion(
    model,
    feature_records,
):
    """
    Predict conversion classification.

    Returns:
        1 = predicted conversion
        0 = predicted non-conversion
    """

    if not feature_records:
        return []

    feature_data = pd.DataFrame(
        feature_records
    )

    predictions = model.predict(
        feature_data
    )

    return [
        int(prediction)
        for prediction in predictions
    ]


def evaluate_conversion_model(
    model,
    feature_records,
    targets,
):
    """
    Evaluate the model on a supplied evaluation dataset.

    This function does not train the model.
    """

    if len(feature_records) != len(targets):
        raise ValueError(
            "Number of feature records must match "
            "number of targets."
        )

    if len(feature_records) == 0:
        raise ValueError(
            "Cannot evaluate model with empty feature data."
        )

    feature_data = pd.DataFrame(
        feature_records
    )

    predictions = model.predict(
        feature_data
    )

    probabilities = model.predict_proba(
        feature_data
    )[:, 1]

    metrics = {
        "accuracy": round(
            float(
                accuracy_score(
                    targets,
                    predictions,
                )
            ),
            4,
        ),
        "precision": round(
            float(
                precision_score(
                    targets,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "recall": round(
            float(
                recall_score(
                    targets,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "f1": round(
            float(
                f1_score(
                    targets,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
    }

    if len(set(targets)) == 2:
        metrics["roc_auc"] = round(
            float(
                roc_auc_score(
                    targets,
                    probabilities,
                )
            ),
            4,
        )
    else:
        metrics["roc_auc"] = None

    return metrics


def train_test_conversion_model(
    feature_records,
    targets,
    test_size=0.20,
    random_state=42,
):
    """
    Split the dataset into training and testing data,
    train the Logistic Regression model on the training
    data, and evaluate it on unseen test data.

    This is the preferred development workflow.
    """

    if len(feature_records) != len(targets):
        raise ValueError(
            "Number of feature records must match "
            "number of targets."
        )

    if len(feature_records) < 10:
        raise ValueError(
            "At least 10 records are recommended "
            "for train/test development."
        )

    feature_data = pd.DataFrame(
        feature_records
    )

    target_data = pd.Series(
        targets
    )

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = train_test_split(
        feature_data,
        target_data,
        test_size=test_size,
        random_state=random_state,
        stratify=target_data,
    )

    model = build_conversion_model()

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    metrics = {
        "accuracy": round(
            float(
                accuracy_score(
                    y_test,
                    predictions,
                )
            ),
            4,
        ),
        "precision": round(
            float(
                precision_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "recall": round(
            float(
                recall_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "f1": round(
            float(
                f1_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),
            4,
        ),
        "roc_auc": round(
            float(
                roc_auc_score(
                    y_test,
                    probabilities,
                )
            ),
            4,
        ),
    }

    return {
        "model": model,
        "metrics": metrics,
        "train_records": len(X_train),
        "test_records": len(X_test),
        "train_converted": int(
            y_train.sum()
        ),
        "test_converted": int(
            y_test.sum()
        ),
    }

