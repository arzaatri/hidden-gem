"""Pure scoring functions for ContentBasedGemFinder — no I/O, easy to test in isolation."""

from __future__ import annotations

import numpy as np


def weighted_jaccard(tags_a: set[str], tags_b: set[str], idf: dict[str, float]) -> float | None:
    """IDF-weighted Jaccard similarity. `None` if both sides have no tags (no signal)."""
    union = tags_a | tags_b
    if not union:
        return None
    intersection = tags_a & tags_b
    denominator = sum(idf.get(tag, 0.0) for tag in union)
    if denominator == 0:
        return 0.0
    numerator = sum(idf.get(tag, 0.0) for tag in intersection)
    return numerator / denominator


def cosine_similarity(vec_a: np.ndarray | None, vec_b: np.ndarray | None) -> float | None:
    """`None` if either vector is missing (e.g. no storyline to embed)."""
    if vec_a is None or vec_b is None:
        return None
    return float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))


def normalize(raw_scores: list[float | None]) -> list[float | None]:
    """Min-max scales the non-`None` values in `raw_scores` to [0, 1]; `None`s pass through.

    Puts differently-scaled signals (e.g. keyword Jaccard vs. embedding cosine
    similarity) on a comparable footing before they're combined.
    """
    available = [score for score in raw_scores if score is not None]
    if not available:
        return raw_scores
    low, high = min(available), max(available)
    if high == low:
        return [None if score is None else 1.0 for score in raw_scores]
    return [None if score is None else (score - low) / (high - low) for score in raw_scores]


def weighted_average(scores: dict[str, float | None], weights: dict[str, float]) -> float:
    """Weighted sum over whatever signals are available, with weights renormalized
    to sum to 1 over just those — a missing signal doesn't count as a 0."""
    available = {name: score for name, score in scores.items() if score is not None}
    if not available:
        return 0.0
    weight_total = sum(weights[name] for name in available)
    if weight_total == 0:
        return 0.0
    return sum(weights[name] * score for name, score in available.items()) / weight_total
