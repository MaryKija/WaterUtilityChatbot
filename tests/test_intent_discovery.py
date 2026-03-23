from backend.intent_discovery import (
    score_and_prune_clusters,
    cluster_embeddings,
)


def test_cluster_embeddings_empty_ok():
    assert cluster_embeddings([]) == []


def test_score_and_prune_clusters_basic():
    texts = [
        "my payment not reflected",
        "i paid but still unpaid",
        "payment missing on my account",
        "i paid at the office",
        "cash payment not updated",
        "bank payment not showing",
        "hello",
    ]
    # Put first 6 into one cluster, last as noise
    labels = [0, 0, 0, 0, 0, 0, -1]
    suggestions = score_and_prune_clusters(labels, texts)
    assert isinstance(suggestions, list)
    assert len(suggestions) >= 1
    assert suggestions[0].suggestion_id.startswith("SUG-")

