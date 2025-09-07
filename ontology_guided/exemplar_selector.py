import re
import math

from collections import Counter
from typing import List, Dict, Any

RETRIEVAL_METHOD = "tfidf_cosine"


def _tokenize(text: str) -> List[str]:
    """Simple tokenization: lowercase alphanumeric words."""
    return re.findall(r"\w+", text.lower())


def _tfidf_vectors(docs: List[List[str]]) -> List[Dict[str, float]]:
    """Compute basic TF-IDF vectors for a list of tokenized documents."""
    df = Counter()
    for tokens in docs:
        df.update(set(tokens))
    N = len(docs)
    vectors: List[Dict[str, float]] = []
    for tokens in docs:
        tf = Counter(tokens)
        vec: Dict[str, float] = {}
        for term, freq in tf.items():
            idf = math.log((N + 1) / (df[term] + 1)) + 1.0
            vec[term] = (freq / len(tokens)) * idf
        vectors.append(vec)
    return vectors


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def select_examples(sentence: str, dev_pool: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    """Return the ``k`` most similar examples from ``dev_pool``.

    Similarity is computed using a simple TF-IDF representation and cosine
    similarity. Each item in ``dev_pool`` should contain a natural language
    sentence under one of the keys ``'user'``, ``'sentence'`` or ``'text'``.
    """
    if not dev_pool or k <= 0:
        return []

    texts = [sentence]
    for ex in dev_pool:
        texts.append(ex.get("user") or ex.get("sentence") or ex.get("text") or "")

    tokenized = [_tokenize(t) for t in texts]
    vectors = _tfidf_vectors(tokenized)
    query_vec = vectors[0]
    pool_vecs = vectors[1:]
    sims = [_cosine(query_vec, vec) for vec in pool_vecs]
    topk_idx = sorted(range(len(dev_pool)), key=lambda i: sims[i], reverse=True)[:k]
    return [dev_pool[i] for i in topk_idx]
