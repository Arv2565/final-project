"""Entity & relation enrichment utilities for GraphRAG.

Provides normalization, fuzzy grouping/deduplication, document-level detection,
and relation enrichment mapping used by the GraphRAG indexer.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import unicodedata
from typing import Iterable, List, Dict, Tuple

import logging
logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize entity names: unicode normalize, strip, collapse whitespace, lower-case.

    Keeps original punctuation (legal names sometimes require exact punctuation) but
    performs safe normalizations to reduce node proliferation.
    """
    if not name:
        return ""
    # Unicode normalization
    n = unicodedata.normalize("NFKC", name)
    # Collapse whitespace and trim
    n = re.sub(r"\s+", " ", n).strip()
    # Lowercase for normalization (keep a sanitized form)
    n_lower = n.lower()
    return n_lower


def fuzzy_group(names: Iterable[str], threshold: float = 0.85) -> Dict[str, List[str]]:
    """Group similar names into canonical buckets using difflib similarity.

    Returns mapping canonical_name -> list of variants.
    Greedy single-link clustering.
    """
    names = [n for n in {n for n in names} if n]
    normalized = {n: normalize_name(n) for n in names}
    buckets: List[List[str]] = []
    used = set()
    for n in names:
        if n in used:
            continue
        canon = n
        bucket = [n]
        used.add(n)
        for m in names:
            if m in used:
                continue
            score = difflib.SequenceMatcher(a=normalized[n], b=normalized[m]).ratio()
            if score >= threshold:
                bucket.append(m)
                used.add(m)
        buckets.append(bucket)
    result = {b[0]: b for b in buckets}
    return result


def canonicalize_entities(names: Iterable[str], threshold: float = 0.85) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Return (name_to_canonical, canonical_to_variants).

    name_to_canonical maps original name -> chosen canonical (first seen in its bucket).
    """
    groups = fuzzy_group(names, threshold=threshold)
    name_to_canon: Dict[str, str] = {}
    for canon, variants in groups.items():
        # choose shortest normalized as canonical candidate
        sorted_variants = sorted(variants, key=lambda x: len(normalize_name(x)))
        chosen = sorted_variants[0]
        for v in variants:
            name_to_canon[v] = chosen
    return name_to_canon, groups


def enrich_relation(rel: str) -> str:
    """Map relation surface forms to enriched semantic tags used in the graph.

    Example: 'amends' -> 'amendment_of', 'cites' -> 'cited_in'
    """
    if not rel:
        return "related_to"
    r = rel.strip().lower()
    mapping = {
        "amend": "amendment_of",
        "amends": "amendment_of",
        "amended by": "amended_by",
        "amended": "amendment_of",
        "cite": "cited_in",
        "cites": "cited_in",
        "refer": "referenced_in",
        "refers": "referenced_in",
        "referenced in": "referenced_in",
        "judged by": "judged_by",
        "judged": "judged_by",
        "enforce": "enforced_by",
        "enforced by": "enforced_by",
        "related to": "related_to",
        "related": "related_to",
    }
    # simple exact or substring mapping
    for k, v in mapping.items():
        if k in r:
            return v
    # fallback: safe slug
    tag = re.sub(r"[^a-z0-9_]+", "_", r).strip("_")
    return tag or "related_to"


def detect_doc_level_from_source(source_path: str) -> str:
    """Heuristic to detect document level (constitution, central_act, state_act, regulation, case_law).

    Uses simple path/filename heuristics; can be replaced by a real registry.
    """
    p = source_path.lower()
    if "constitution" in p:
        return "constitution"
    if "ipc" in p or "act" in p or "acts" in p or "central_acts" in p:
        return "statute"
    if "crpc" in p or "cpc" in p or "nia" in p:
        return "statute"
    if "case" in p or "judgment" in p or "judgement" in p:
        return "case_law"
    if "regulation" in p or "rule" in p:
        return "regulation"
    # default
    return "unknown"
