DEFAULT_SEGMENT_PRIORITY = [
    "High Value",
    "Active",
    "Prospect/New",
    "At Risk",
    "Low Value",
    "Unengaged",
]


def assign_customer_segment(
    customer,
    segment_priority=None,
):
    """
    Assign a business segment using configurable,
    priority-based rules.

    The function expects customer-level features
    produced by the Customer Intelligence feature layer.
    """

    priority = segment_priority or DEFAULT_SEGMENT_PRIORITY

    rules = {
        "High Value": (
            customer.get("customer_value") == "High Value"
        ),
        "Active": (
            customer.get("active_leads", 0) > 0
        ),
        "Prospect/New": (
            customer.get("lead_count", 0) > 0
            and not customer.get("has_transaction", False)
        ),
        "At Risk": (
            customer.get("has_transaction", False)
            and customer.get("active_leads", 0) == 0
        ),
        "Low Value": (
            customer.get("customer_value") == "Low Value"
        ),
        "Unengaged": (
            customer.get("lead_count", 0) == 0
            and not customer.get("has_transaction", False)
        ),
    }

    for segment in priority:
        if rules.get(segment, False):
            return segment

    return "Unclassified"


def segment_customers(
    customer_features,
    rfm_results=None,
    segment_priority=None,
):
    """
    Apply the rule-based segmentation engine to
    customer-level feature data.

    RFM results are supplied separately so the segmentation
    engine remains reusable and does not calculate RFM itself.
    """

    rfm_results = rfm_results or {}

    segmented_customers = []

    for customer in customer_features:
        customer_data = customer.copy()

        customer_id = customer_data["customer_id"]

        rfm = rfm_results.get(customer_id)

        if rfm:
            customer_data["customer_value"] = rfm.get(
                "customer_value"
            )
            customer_data["rfm"] = rfm
        else:
            customer_data["customer_value"] = None
            customer_data["rfm"] = None

        customer_data["has_transaction"] = int(
            customer_data.get("transaction_count", 0) > 0
        )

        customer_data["segment"] = assign_customer_segment(
            customer_data,
            segment_priority=segment_priority,
        )

        segmented_customers.append(customer_data)

    return segmented_customers