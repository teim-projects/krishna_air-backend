from datetime import date


DEFAULT_VALUE_THRESHOLDS = {
    "high": 12,
    "medium": 9,
}


def calculate_rfm(transaction_features, analysis_date):
    """
    Calculate RFM metrics and rank-based RFM scores.

    Parameters
    ----------
    transaction_features : dict
        Customer-level transaction information keyed by customer ID.

    analysis_date : date
        Date used as the reference point for recency.

    Returns
    -------
    dict
        RFM results keyed by customer ID.
    """

    rfm_customers = {}

    for customer_id, data in transaction_features.items():
        transaction_count = data.get("transaction_count", 0)
        latest_invoice = data.get("latest_invoice")
        monetary = float(data.get("monetary", 0) or 0)

        if transaction_count > 0 and latest_invoice:
            recency = (analysis_date - latest_invoice).days

            rfm_customers[customer_id] = {
                "recency": recency,
                "frequency": transaction_count,
                "monetary": monetary,
            }

    if not rfm_customers:
        return {}

    # Recency: lower number of days is better.
    recency_sorted = sorted(
        rfm_customers.items(),
        key=lambda x: (x[1]["recency"], x[0])
    )

    # Frequency: higher number of transactions is better.
    frequency_sorted = sorted(
        rfm_customers.items(),
        key=lambda x: (x[1]["frequency"], -x[0])
    )

    # Monetary: higher revenue is better.
    monetary_sorted = sorted(
        rfm_customers.items(),
        key=lambda x: (x[1]["monetary"], x[0])
    )

    total_rfm_customers = len(rfm_customers)

    for position, (customer_id, data) in enumerate(
        recency_sorted,
        start=1
    ):
        data["R"] = total_rfm_customers - position + 2

    for position, (customer_id, data) in enumerate(
        reversed(frequency_sorted),
        start=1
    ):
        data["F"] = total_rfm_customers - position + 2

    for position, (customer_id, data) in enumerate(
        reversed(monetary_sorted),
        start=1
    ):
        data["M"] = total_rfm_customers - position + 2

    # Create RFM score and customer-value classification.
    for customer_id, data in rfm_customers.items():
        data["rfm_score"] = (
            f"{data['R']}"
            f"{data['F']}"
            f"{data['M']}"
        )

        total_score = (
            data["R"]
            + data["F"]
            + data["M"]
        )

        if total_score >= DEFAULT_VALUE_THRESHOLDS["high"]:
            data["customer_value"] = "High Value"
        elif total_score >= DEFAULT_VALUE_THRESHOLDS["medium"]:
            data["customer_value"] = "Medium Value"
        else:
            data["customer_value"] = "Low Value"

    return rfm_customers