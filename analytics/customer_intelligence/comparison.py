from collections import Counter


def compare_rule_and_ml_segments(
    customer_features,
    cluster_labels,
):
    """
    Compare rule-based customer segments with
    K-Means cluster assignments.

    Returns cluster-level dominant rule segments
    and alignment percentages.
    """

    if len(customer_features) != len(cluster_labels):
        raise ValueError(
            "Customer features and cluster labels "
            "must have the same length."
        )

    cluster_segments = {}

    for customer, label in zip(
        customer_features,
        cluster_labels,
    ):
        cluster = int(label)
        segment = customer.get(
            "segment",
            "Unclassified",
        )

        cluster_segments.setdefault(
            cluster,
            [],
        ).append(segment)

    comparisons = []

    for cluster in sorted(cluster_segments):
        segments = cluster_segments[cluster]
        counts = Counter(segments)

        dominant_segment, dominant_count = (
            counts.most_common(1)[0]
        )

        alignment = (
            dominant_count / len(segments)
        ) * 100

        comparisons.append(
            {
                "cluster": cluster,
                "customer_count": len(segments),
                "dominant_rule_segment": (
                    dominant_segment
                ),
                "dominant_segment_count": (
                    dominant_count
                ),
                "alignment_percentage": round(
                    alignment,
                    2,
                ),
                "rule_segment_distribution": dict(
                    counts
                ),
            }
        )

    return comparisons