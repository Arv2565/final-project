"""Human-in-the-loop validation helpers.

Provides simple heuristics to flag uncertain triples for manual review and
append them to a review queue file for later inspection by domain experts.
"""
from __future__ import annotations

import json
import os
from typing import Iterable, List, Dict
import logging

logger = logging.getLogger(__name__)


def _default_review_path() -> str:
    # store a queue file under data/processed/extracted for convenience
    base = os.path.join(os.getcwd(), "data", "processed", "extracted")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "review_queue.jsonl")


def score_triple(head: str, relation: str, tail: str) -> float:
    """Very small heuristic scoring: higher is more confident.

Rules:
- penalize if head==tail
- penalize if short tokens
- reward when relation is longer/descriptive
"""
    score = 1.0
    if not head or not tail or not relation:
        return 0.0
    if head.strip().lower() == tail.strip().lower():
        score -= 0.6
    # simple length-based heuristics
    if len(head.strip()) < 3:
        score -= 0.2
    if len(tail.strip()) < 3:
        score -= 0.2
    if len(relation.strip()) < 3:
        score -= 0.3
    return max(0.0, score)


def flag_uncertain_triples(triples: Iterable[Dict], threshold: float = 0.6, review_path: str | None = None) -> List[Dict]:
    """Flag triples with score below threshold and append them to a review queue file.

    Each triple dict is expected to have keys: head, relation, tail, and optional metadata.
    Returns the list of flagged triples.
    """
    if review_path is None:
        review_path = _default_review_path()
    flagged = []
    with open(review_path, "a", encoding="utf-8") as fh:
        for t in triples:
            head = t.get("head") if isinstance(t, dict) else None
            rel = t.get("relation") if isinstance(t, dict) else None
            tail = t.get("tail") if isinstance(t, dict) else None
            score = score_triple(head or "", rel or "", tail or "")
            entry = dict(head=head, relation=rel, tail=tail, score=score)
            if score < threshold:
                flagged.append(entry)
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if flagged:
        logger.info(f"Appended {len(flagged)} triples to review queue: {review_path}")
    return flagged
