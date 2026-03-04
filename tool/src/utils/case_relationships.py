"""
Case Relationships Utility for Case Retrieval Module.

This module handles extraction and inference of relationships between cases,
including appellate chains, precedent citations, and case cross-references.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CaseReference:
    """Represents a reference to another case within a judgment."""
    case_id: Optional[str]  # e.g., "2000 SC 359" or inferred ID
    citation: str  # e.g., "(2000) 6 SCC 359"
    case_name: Optional[str]  # Party names or case title
    relationship_type: str  # "cites", "follows", "distinguishes", "overrules", etc.
    confidence: float  # 0.0 to 1.0


@dataclass
class AppellateChain:
    """Represents the appellate relationship between two cases."""
    lower_case_id: str
    lower_court: str
    upper_case_id: str
    upper_court: str
    reversal_status: str  # "UPHELD", "REVERSED", "MODIFIED", "REMANDED", "UNKNOWN"
    confidence: float  # 0.0 to 1.0
    reversal_reason: Optional[str] = None


# Patterns for extracting case citations
CITATION_PATTERNS = [
    # Standard SCC format: (YYYY) X SCC Y
    r"\((\d{4})\)\s+(\d+)\s+SCC\s+(\d+)",
    # AIR format: AIR YYYY SC/HC Z
    r"AIR\s+(\d{4})\s+(SC|HC|Delhi|Kerala|Bombay|Karnataka|Madras)\s+(\d+)",
    # Old SCR format: [YYYY] X SCR Y
    r"\[(\d{4})\]\s+(\d+)\s+S\.C\.?R\.?\s+(\d+)",
    # Case law database format
    r"(\d{4})\s+(?:SCC|AIR|SCR)\s+\((?:S|I)\)\s+(\d+)",
    # Citation number format: INSC NNNNN or INHC NNNNN
    r"IN(?:SC|HC|[A-Z]{2})\s+(\d{4,6})",
]

# Patterns for extracting case names/parties
CASE_NAME_PATTERN = r"(?:Case|Matter|Appeal|Petition|Writ)\s+(?:No\.?|#)?\s*['\"]?([^'\"]*?[A-Za-z\s]+)['\"]?\s+(?:v\.?|vs\.?|versus)"

# Reversal indicators
REVERSAL_KEYWORDS = {
    "upheld": ("UPHELD", 0.8),
    "upheld in": ("UPHELD", 0.9),
    "affirmed": ("UPHELD", 0.8),
    "confirmation": ("UPHELD", 0.7),
    "agreed with": ("UPHELD", 0.6),
    
    "reversed": ("REVERSED", 0.9),
    "set aside": ("REVERSED", 0.9),
    "quashed": ("REVERSED", 0.85),
    "overruled": ("REVERSED", 0.8),
    "overturned": ("REVERSED", 0.85),
    "struck down": ("REVERSED", 0.8),
    
    "modified": ("MODIFIED", 0.8),
    "modified": ("MODIFIED", 0.8),
    "reduced": ("MODIFIED", 0.7),
    "enhanced": ("MODIFIED", 0.7),
    "partly allowed": ("MODIFIED", 0.7),
    
    "remanded": ("REMANDED", 0.85),
    "remitted": ("REMANDED", 0.85),
    "sent back": ("REMANDED", 0.7),
}

# Relationship type indicators
RELATIONSHIP_PATTERNS = {
    "overrules": r"(?:this\s+court\s+)?\w+(?:ed|s)?\s+(?:held|laid down|decided|approved)\s+in\s+\[?\d{4}\]?\s*\d+\s+\w+\s+\d+",
    "follows": r"(?:following|in accordance with|pursuant to|relying on)\s+\[?\d{4}\]?\s*\d+\s+\w+\s+\d+",
    "distinguishes": r"(?:distinguished|distinguishable from)\s+\[?\d{4}\]?\s*\d+\s+\w+\s+\d+",
    "cites": r"(?:cited|referred to|relied upon)\s+(?:with approval)?\s*\[?\d{4}\]?\s*\d+\s+\w+\s+\d+",
}

# Appellate context patterns
APPELLATE_INDICATORS = [
    r"(?:appeal\s+(?:from|against)|petition\s+(?:for|against|under))",
    r"(?:high court|district court|trial court)\s+(?:order|judgment|decision)\s+(?:dated|of)",
    r"(?:special leave\s+petition|slp|writ petition)",
    r"(?:lower court|subordinate court|first court)\s+(?:order|decision)",
]


def extract_case_citations(judgment_text: str) -> List[Tuple[str, int]]:
    """
    Extract all case citations from judgment text.
    
    Args:
        judgment_text: Full judgment text
    
    Returns:
        List of (citation_string, start_position) tuples
    
    Example:
        >>> text = "This case follows (2000) 6 SCC 359 and (2020) 10 SCC 240"
        >>> extract_case_citations(text)
        [('(2000) 6 SCC 359', 22), ('(2020) 10 SCC 240', 51)]
    """
    citations = []
    
    for pattern in CITATION_PATTERNS:
        for match in re.finditer(pattern, judgment_text, re.IGNORECASE):
            citation = match.group(0)
            start = match.start()
            citations.append((citation, start))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_citations = []
    for citation, start in citations:
        if citation not in seen:
            seen.add(citation)
            unique_citations.append((citation, start))
    
    return sorted(unique_citations, key=lambda x: x[1])


def infer_precedent_relationships(judgment_text: str, current_case_citation: str) -> List[CaseReference]:
    """
    Infer precedent relationships from judgment text.
    
    Analyzes how the current case treats cited precedents (follows, distinguishes, overrules).
    
    Args:
        judgment_text: Full judgment text
        current_case_citation: Citation of the current case (for context)
    
    Returns:
        List of CaseReference objects with inferred relationships
    """
    references = []
    citations = extract_case_citations(judgment_text)
    
    if not citations:
        return references
    
    # Context window: 200 characters around citation
    CONTEXT_WINDOW = 200
    
    for citation, position in citations:
        context_start = max(0, position - CONTEXT_WINDOW)
        context_end = min(len(judgment_text), position + len(citation) + CONTEXT_WINDOW)
        context = judgment_text[context_start:context_end].lower()
        
        # Determine relationship type
        relationship_type = "cites"  # default
        confidence = 0.6
        
        for rel_type, pattern in RELATIONSHIP_PATTERNS.items():
            if re.search(pattern, context, re.IGNORECASE):
                relationship_type = rel_type
                confidence = 0.8
                break
        
        # Try to extract case name from context
        case_name_match = re.search(CASE_NAME_PATTERN, context, re.IGNORECASE)
        case_name = case_name_match.group(1) if case_name_match else None
        
        reference = CaseReference(
            case_id=None,  # Would be populated from citation lookup
            citation=citation,
            case_name=case_name,
            relationship_type=relationship_type,
            confidence=confidence
        )
        references.append(reference)
    
    logger.debug(f"Extracted {len(references)} precedent references from judgment")
    return references


def extract_appellate_pattern(judgment_text: str) -> Optional[Tuple[str, str]]:
    """
    Extract appellate pattern from judgment indicating case comes from another court.
    
    Returns: (lower_court_designation, finding) or None
    
    Args:
        judgment_text: Judgment text
    
    Returns:
        Tuple of (lower_court_type, finding_context) if pattern found
    
    Example:
        >>> text = "This is an appeal from the High Court of Kerala dated..."
        >>> extract_appellate_pattern(text)
        ('High Court of Kerala', 'appeal from')
    """
    for pattern in APPELLATE_INDICATORS:
        match = re.search(pattern, judgment_text, re.IGNORECASE)
        if match:
            context_start = max(0, match.start() - 50)
            context_end = min(len(judgment_text), match.end() + 100)
            context = judgment_text[context_start:context_end]
            return (match.group(0), context)
    
    return None


def detect_reversal_status(judgment_text: str, threshold: float = 0.7) -> Tuple[str, float]:
    """
    Detect reversal status from judgment text.
    
    Searches for keywords indicating how the court handled the lower court decision.
    
    Args:
        judgment_text: Judgment text
        threshold: Confidence threshold for classification
    
    Returns:
        Tuple of (reversal_status, confidence)
        Status can be: UPHELD, REVERSED, MODIFIED, REMANDED, UNKNOWN
    
    Example:
        >>> text = "The High Court order was set aside by this court."
        >>> detect_reversal_status(text)
        ('REVERSED', 0.9)
    """
    if not judgment_text:
        return ("UNKNOWN", 0.0)
    
    text_lower = judgment_text.lower()
    
    # Track all matches with confidence
    matches: Dict[str, float] = {}
    
    for keyword, (status, conf) in REVERSAL_KEYWORDS.items():
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, text_lower):
            if status not in matches:
                matches[status] = conf
            else:
                matches[status] = max(matches[status], conf)
    
    if not matches:
        return ("UNKNOWN", 0.0)
    
    # Return highest confidence match
    best_status = max(matches, key=matches.get)
    best_confidence = matches[best_status]
    
    if best_confidence < threshold:
        return ("UNKNOWN", best_confidence)
    
    return (best_status, best_confidence)


def infer_case_hierarchy(case_metadata: Dict, judgment_text: str) -> Optional[AppellateChain]:
    """
    Infer case hierarchy/appellate relationship from metadata and text.
    
    Attempts to detect if this case is an appeal from another and the nature of the reversal.
    
    Args:
        case_metadata: Case metadata dict with fields like 'court', 'citation', 'date'
        judgment_text: Full judgment text
    
    Returns:
        AppellateChain if appellate relationship detected, None otherwise
    """
    # Check for appellate pattern in text
    appellate_info = extract_appellate_pattern(judgment_text)
    if not appellate_info:
        return None
    
    lower_court_hint, context = appellate_info
    
    # Detect reversal status
    reversal_status, reversal_confidence = detect_reversal_status(judgment_text)
    
    # Build chain if confidence is reasonable
    if reversal_confidence < 0.5:
        reversal_status = "UNKNOWN"
    
    chain = AppellateChain(
        lower_case_id="",  # Would be populated by case matching
        lower_court=lower_court_hint,
        upper_case_id=case_metadata.get("citation", ""),
        upper_court=case_metadata.get("court", ""),
        reversal_status=reversal_status,
        confidence=reversal_confidence,
        reversal_reason=None
    )
    
    logger.debug(f"Inferred appellate chain: {lower_court_hint} → {case_metadata.get('court')} ({reversal_status})")
    return chain


def extract_common_citations_between_cases(case1_text: str, case2_text: str) -> Set[str]:
    """
    Find common case citations between two judgments.
    
    Useful for detecting precedent overlap and relationship.
    
    Args:
        case1_text: First judgment text
        case2_text: Second judgment text
    
    Returns:
        Set of citation strings common to both
    """
    citations1 = {citation for citation, _ in extract_case_citations(case1_text)}
    citations2 = {citation for citation, _ in extract_case_citations(case2_text)}
    
    return citations1 & citations2


def build_case_relationship_summary(
    case1_citation: str,
    case2_citation: str,
    common_citations: Set[str],
    reversal_status: str,
    relationship_confidence: float
) -> Dict:
    """
    Build a structured summary of relationship between two cases.
    
    Args:
        case1_citation: First case citation
        case2_citation: Second case citation
        common_citations: Set of shared precedent citations
        reversal_status: Detected reversal status
        relationship_confidence: Overall confidence in the relationship
    
    Returns:
        Dictionary with relationship details
    """
    return {
        "case_1": case1_citation,
        "case_2": case2_citation,
        "common_precedents": list(common_citations),
        "reversal_status": reversal_status,
        "confidence": relationship_confidence,
        "relationship_type": _infer_relationship_type(reversal_status),
    }


def _infer_relationship_type(reversal_status: str) -> str:
    """Map reversal status to human-readable relationship type."""
    mapping = {
        "REVERSED": "overturned",
        "UPHELD": "affirmed",
        "MODIFIED": "partially reversed",
        "REMANDED": "remanded for reconsideration",
        "UNKNOWN": "related case",
    }
    return mapping.get(reversal_status, "related case")
