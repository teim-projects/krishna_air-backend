import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


DEFAULT_CLUSTER_FEATURES = [
    "lead_count",
    "active_leads",
    "followup_count",
    "transaction_count",
    "revenue",
]


def prepare_customer_features(
    customer_features,
    feature_names=None,
    log_transform_features=None,
):
    """
    Prepare customer-level numerical features for clustering.

    Steps:
    1. Select configurable numerical features.
    2. Convert values to numeric.
    3. Handle missing values using the median.
    4. Apply log1p to selected skewed features.
    5. Standardize all features.
    """

    feature_names = feature_names or DEFAULT_CLUSTER_FEATURES
    log_transform_features = log_transform_features or ["revenue"]

    customer_ids = [
        customer["customer_id"]
        for customer in customer_features
    ]

    matrix = []

    for customer in customer_features:
        row = []

        for feature in feature_names:
            value = customer.get(feature)

            try:
                value = float(value)
            except (TypeError, ValueError):
                value = np.nan

            row.append(value)

        matrix.append(row)

    X = np.array(matrix, dtype=float)

    # Handle missing numerical values.
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(X)

    # Log-transform highly skewed positive features such as revenue.
    for index, feature in enumerate(feature_names):
        if feature in log_transform_features:
            X[:, index] = np.log1p(np.maximum(X[:, index], 0))

    # Standardize features so different scales do not dominate K-Means.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return {
        "customer_ids": customer_ids,
        "feature_names": feature_names,
        "X": X,
        "X_scaled": X_scaled,
        "imputer": imputer,
        "scaler": scaler,
    }