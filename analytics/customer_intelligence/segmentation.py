from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def evaluate_kmeans(
    X_scaled,
    k_range=range(2, 7),
    random_state=42,
):
    """
    Evaluate K-Means for multiple values of K.

    Returns inertia and silhouette score for each K.
    """

    results = []

    for k in k_range:
        model = KMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=10,
        )

        labels = model.fit_predict(X_scaled)

        results.append(
            {
                "k": k,
                "inertia": model.inertia_,
                "silhouette": silhouette_score(
                    X_scaled,
                    labels,
                ),
            }
        )

    return results


def fit_kmeans(
    X_scaled,
    n_clusters,
    random_state=42,
):
    """
    Fit the final K-Means model.
    """

    model = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,
    )

    labels = model.fit_predict(X_scaled)

    return {
        "model": model,
        "labels": labels,
        "n_clusters": n_clusters,
    }


def select_best_k(evaluation_results):
    """
    Select K using the highest silhouette score.

    Inertia is retained as an evaluation metric,
    while silhouette score determines the recommended K.
    """

    if not evaluation_results:
        raise ValueError(
            "No K-Means evaluation results provided."
        )

    best_result = max(
        evaluation_results,
        key=lambda result: result["silhouette"],
    )

    return best_result["k"]