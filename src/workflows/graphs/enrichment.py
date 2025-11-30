"""Entity & relation enrichment utilities for GraphRAG.

Provides legal entity-specific normalization, structured parsing, deduplication,
document-level detection, and relation enrichment mapping used by the GraphRAG indexer.

Key improvements over previous version:
  - Legal entity parsers for statute references, sections, and case citations
  - Type-specific matching to prevent false duplicates ("Section 420" vs "IPC 420")
  - Fallback to fuzzy matching (0.80 threshold) only when structured parsing fails
  - Canonical ID generation for all legal entities
"""
from __future__ import annotations

import difflib
import json
import os
import re
import unicodedata
from typing import Iterable, List, Dict, Tuple, Optional

import logging

from src.utils.entity_resolver import EntityResolver
from src.utils.legal_entity_parser import (
    LegalEntityParser, SectionReference, CaseCitation, StatuteReference
)

logger = logging.getLogger(__name__)

# Global entity resolver instance (shared across module)
_resolver: Optional[EntityResolver] = None


def get_resolver(strict_mode: bool = False) -> EntityResolver:
    """Get or create global entity resolver.
    
    Args:
        strict_mode: If True, only high-confidence structured matches are accepted.
                    If False, fuzzy matching is used as fallback.
    """
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver(strict_mode=strict_mode)
    return _resolver


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
    # Lowercase for normalization
    n_lower = n.lower()
    return n_lower


def fuzzy_group(names: Iterable[str], threshold: float = 0.85) -> Dict[str, List[str]]:
    """Group similar names into canonical buckets using difflib similarity.

    Returns mapping canonical_name -> list of variants.
    Greedy single-link clustering.
    
    NOTE: This is now used only as FALLBACK for non-legal entities.
    For legal entities (sections, statutes, cases), use entity_resolver instead.
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


def canonicalize_entities_legal(names: Iterable[str], entity_type: Optional[str] = None, 
                                strict_mode: bool = False) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Return (name_to_canonical, canonical_to_variants) using legal entity parsing.

    This is the primary canonicalization method for legal documents.
    Attempts structured parsing first, falls back to fuzzy matching if needed.
    
    Args:
        names: Entity names to canonicalize
        entity_type: Optional hint ('Section', 'Case', 'Statute')
        strict_mode: If True, only high-confidence matches create clusters
        
    Returns:
        Tuple of (name_to_canonical_id, canonical_id_to_variants)
    """
    resolver = EntityResolver(strict_mode=strict_mode)
    name_to_canonical: Dict[str, str] = {}
    canonical_to_variants: Dict[str, List[str]] = {}

    for name in names:
        if not name or name in name_to_canonical:
            continue

        # Try to resolve using legal entity resolver
        canonical_id = resolver.get_canonical_id(name, entity_type)
        
        if canonical_id:
            name_to_canonical[name] = canonical_id
            if canonical_id not in canonical_to_variants:
                canonical_to_variants[canonical_id] = []
            canonical_to_variants[canonical_id].append(name)
        else:
            # If resolution failed, use name as its own canonical (singleton cluster)
            name_to_canonical[name] = name
            canonical_to_variants[name] = [name]

    return name_to_canonical, canonical_to_variants


def canonicalize_entities(names: Iterable[str], threshold: float = 0.85) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Return (name_to_canonical, canonical_to_variants).

    DEPRECATED: Use canonicalize_entities_legal() for legal documents.
    This function is kept for backward compatibility and non-legal entity resolution.
    
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


def normalize_relation_for_typed_relationships(rel: str) -> str:
    """Normalize relation to canonical form for use with typed relationships.
    
    Ensures the relation is in canonical form (e.g., 'amends', 'cites', 'part_of')
    so it can be properly converted to a Neo4j typed relationship label.
    
    This function:
    1. Normalizes the relation using LegalOntology.normalize_relation()
    2. Returns the canonical form for use in typed relationship creation
    3. Logs low-confidence relations for monitoring
    
    Args:
        rel: Relation string (may be in various surface forms)
        
    Returns:
        Canonical relation type for use with typed relationships (e.g., 'amends', 'cites')
        
    Example:
        >>> normalize_relation_for_typed_relationships('amend')
        'amends'
        >>> normalize_relation_for_typed_relationships('cites')
        'cites'
        >>> normalize_relation_for_typed_relationships('unknown_type')
        'unknown_type'  # returns with low confidence
    """
    from src.config.legal_ontology import LegalOntology
    
    if not rel:
        return "related_to"
    
    # Use LegalOntology's normalization
    canonical_rel, confidence = LegalOntology.normalize_relation(rel)
    
    # Log if normalization confidence is low
    if confidence < 0.8:
        logger.debug(f"Low-confidence relation normalization: '{rel}' -> '{canonical_rel}' (confidence: {confidence})")
    
    return canonical_rel



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
