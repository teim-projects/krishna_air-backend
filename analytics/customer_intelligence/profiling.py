def profile_clusters(
    customer_features,
    labels,
    feature_names,
):
    """
    Create customer-level cluster profiles.

    Parameters
    ----------
    customer_features : list of dict
        Customer-level feature rows.

    labels : array-like
        Cluster label for each customer.

    feature_names : list
        Numerical features used for clustering.

    Returns
    -------
    list of dict
        Cluster-level summary statistics.
    """

    if len(customer_features) != len(labels):
        raise ValueError(
            "Customer features and cluster labels "
            "must have the same length."
        )

    clusters = {}

    for customer, label in zip(
        customer_features,
        labels,
    ):
        cluster = int(label)

        if cluster not in clusters:
            clusters[cluster] = []

        clusters[cluster].append(customer)

    profiles = []

    for cluster in sorted(clusters):
        cluster_customers = clusters[cluster]

        profile = {
            "cluster": cluster,
            "customer_count": len(cluster_customers),
        }

        for feature in feature_names:
            values = [
                float(customer.get(feature, 0) or 0)
                for customer in cluster_customers
            ]

            average = sum(values) / len(values)

            profile[f"avg_{feature}"] = round(
                average,
                2,
            )

        profiles.append(profile)

    return profiles