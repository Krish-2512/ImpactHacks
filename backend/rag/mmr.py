"""
Max Marginal Relevance (MMR) selection.
Picks diverse results by balancing relevance to query vs similarity to
already-selected results — avoids returning near-duplicate chunks.
"""
import math
from typing import Any


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-9)


def mmr_select(
    candidates: list[dict[str, Any]],
    top_k: int = 5,
    lambda_mult: float = 0.6,
) -> list[dict[str, Any]]:
    """
    candidates: list of dicts with keys {text, source, score, vector}
    lambda_mult: 0 = max diversity, 1 = max relevance (0.6 is a good default)
    Returns top_k selected candidates (vector key removed from output).
    """
    if not candidates:
        return []
    if len(candidates) <= top_k:
        return [{k: v for k, v in c.items() if k != "vector"} for c in candidates]

    selected: list[dict] = []
    remaining = list(candidates)

    # First pick: highest relevance score
    best = max(remaining, key=lambda c: c["score"])
    selected.append(best)
    remaining.remove(best)

    while len(selected) < top_k and remaining:
        mmr_scores = []
        for cand in remaining:
            relevance = cand["score"]
            redundancy = max(
                _cosine(cand["vector"], s["vector"])
                for s in selected
            )
            mmr = lambda_mult * relevance - (1 - lambda_mult) * redundancy
            mmr_scores.append((mmr, cand))

        _, best = max(mmr_scores, key=lambda x: x[0])
        selected.append(best)
        remaining.remove(best)

    return [{k: v for k, v in c.items() if k != "vector"} for c in selected]
