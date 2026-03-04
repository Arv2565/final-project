"""
Court Hierarchy Utility for Case Retrieval Module.

This module manages court level classification and hierarchical relationships.
Provides court level mapping, extraction from case metadata and text, and utilities
for court-based filtering in case retrieval.
"""

import re
import logging
from typing import Optional, Tuple, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class CourtLevel(int, Enum):
    """Enumeration of court hierarchy levels in Indian legal system."""
    SUPREME_COURT = 1
    HIGH_COURT = 2
    LOWER_COURTS = 3  # District/Trial Courts and other lower judicial bodies
    UNKNOWN = 0


# Court hierarchy mapping - maps court names to levels
COURT_HIERARCHY_MAP: Dict[str, CourtLevel] = {
    # Supreme Court
    "supreme court of india": CourtLevel.SUPREME_COURT,
    "supreme court": CourtLevel.SUPREME_COURT,
    "s.c.": CourtLevel.SUPREME_COURT,
    "sc": CourtLevel.SUPREME_COURT,
    
    # High Courts
    "high court of delhi": CourtLevel.HIGH_COURT,
    "high court of bombay": CourtLevel.HIGH_COURT,
    "high court of kerala at ernakulam": CourtLevel.HIGH_COURT,
    "high court of kerala": CourtLevel.HIGH_COURT,
    "high court of karnataka": CourtLevel.HIGH_COURT,
    "high court of madras": CourtLevel.HIGH_COURT,
    "high court of calcutta": CourtLevel.HIGH_COURT,
    "high court": CourtLevel.HIGH_COURT,
    "h.c.": CourtLevel.HIGH_COURT,
    "hc": CourtLevel.HIGH_COURT,
    
    # District/Lower Courts
    "district court": CourtLevel.LOWER_COURTS,
    "civil court": CourtLevel.LOWER_COURTS,
    "criminal court": CourtLevel.LOWER_COURTS,
    "trial court": CourtLevel.LOWER_COURTS,
    "sessions court": CourtLevel.LOWER_COURTS,
    "magistrate court": CourtLevel.LOWER_COURTS,
    "subordinate court": CourtLevel.LOWER_COURTS,
    "labour court": CourtLevel.LOWER_COURTS,
    "family court": CourtLevel.LOWER_COURTS,
    "consumer court": CourtLevel.LOWER_COURTS,
    "tribunal": CourtLevel.LOWER_COURTS,
    "industrial tribunal": CourtLevel.LOWER_COURTS,
    "customs tribunal": CourtLevel.LOWER_COURTS,
}

# Patterns to extract court level information from judgment text
APPELLATE_PATTERNS = [
    r"appeal\s+from\s+(?P<court>\w+(?:\s+court)?)",
    r"(?P<court>high court|district court|trial court)\s+order\s+(?:upheld|reversed|set aside)",
    r"petition\s+against\s+(?P<court>\w+(?:\s+court)?)\s+(?:order|judgment)",
    r"(?P<court>lower court|subordinate court)\s+decision",
]

REVERSAL_PATTERNS = [
    r"(?:high court\s+)?order\s+(?:reversed|set aside|quashed)",
    r"(?:conviction|sentence)\s+(?:uphe|ld|modified|reduced)",
    r"appeal\s+(?:allowed|allowed in part|dismissed)",
    r"remanded\s+(?:to|for)",
]


def get_court_level(court_name: Optional[str], judgment_text: Optional[str] = None) -> CourtLevel:
    """
    Determine court level from court name and optionally from judgment text.
    
    Uses hierarchical approach:
    1. Direct lookup in court_name
    2. Case-insensitive fuzzy matching on court_name
    3. Extract from judgment_text if court_name lookup fails
    
    Args:
        court_name: Name of the court (e.g., "Supreme Court of India")
        judgment_text: Full judgment text for contextual extraction (optional)
    
    Returns:
        CourtLevel enum value (SUPREME_COURT=1, HIGH_COURT=2, LOWER_COURTS=3, UNKNOWN=0)
    
    Examples:
        >>> get_court_level("Supreme Court of India")
        <CourtLevel.SUPREME_COURT: 1>
        
        >>> get_court_level("High Court of Kerala at Ernakulam")
        <CourtLevel.HIGH_COURT: 2>
    """
    if not court_name and not judgment_text:
        return CourtLevel.UNKNOWN
    
    # First attempt: direct lookup with normalization
    if court_name:
        normalized = court_name.lower().strip()
        
        # Try exact match first
        if normalized in COURT_HIERARCHY_MAP:
            return COURT_HIERARCHY_MAP[normalized]
        
        # Try partial/fuzzy match
        for mapped_court, level in COURT_HIERARCHY_MAP.items():
            if mapped_court in normalized or normalized in mapped_court:
                logger.debug(f"Fuzzy matched '{court_name}' to '{mapped_court}' (Level: {level.name})")
                return level
    
    # Second attempt: extract from judgment text
    if judgment_text:
        level = _extract_court_level_from_text(judgment_text)
        if level != CourtLevel.UNKNOWN:
            logger.debug(f"Extracted court level from text: {level.name}")
            return level
    
    # Fallback: unknown
    logger.warning(f"Could not determine court level for: {court_name}")
    return CourtLevel.UNKNOWN


def _extract_court_level_from_text(text: str) -> CourtLevel:
    """
    Extract court level information from judgment text using pattern matching.
    
    This is a secondary method used when court_name is not reliably available.
    
    Args:
        text: Judgment text or case description
    
    Returns:
        CourtLevel found in text, or UNKNOWN
    """
    if not text:
        return CourtLevel.UNKNOWN
    
    text_lower = text.lower()
    
    # Check for explicit court mentions in order of specificity
    for pattern in APPELLATE_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            court_mention = match.group("court").lower()
            for mapped_court, level in COURT_HIERARCHY_MAP.items():
                if mapped_court in court_mention or court_mention in mapped_court:
                    return level
    
    # Check for direct court type mentions
    if re.search(r"\bsupreme court\b", text_lower):
        return CourtLevel.SUPREME_COURT
    elif re.search(r"\bhigh court\b", text_lower):
        # Might be Supreme reviewing High Court - check context
        if re.search(r"appeal from.*high court", text_lower):
            return CourtLevel.HIGH_COURT
        return CourtLevel.HIGH_COURT
    elif re.search(r"\b(?:district|civil|criminal|trial|sessions|magistrate|subordinate)\s+court\b", text_lower):
        return CourtLevel.LOWER_COURTS
    
    return CourtLevel.UNKNOWN


def extract_appellate_chain_hint(judgment_text: str) -> Tuple[Optional[CourtLevel], Optional[CourtLevel]]:
    """
    Extract hints about appellate relationship from judgment text.
    
    Returns: (appealed_from_court_level, current_court_level) or (None, None)
    
    Args:
        judgment_text: Full judgment text
    
    Returns:
        Tuple of court levels if pattern found, otherwise (None, None)
    
    Examples:
        >>> text = "Appeal from High Court of Kerala order dated..."
        >>> extract_appellate_chain_hint(text)
        (<CourtLevel.HIGH_COURT: 2>, None)
    """
    if not judgment_text:
        return (None, None)
    
    text_lower = judgment_text.lower()
    
    # Pattern: "Appeal from [court] order/judgment"
    match = re.search(r"appeal\s+from\s+(?P<court>[\w\s]+?)\s+(?:order|judgment|decision)", text_lower)
    if match:
        court_name = match.group("court").strip()
        level = get_court_level(court_name)
        if level != CourtLevel.UNKNOWN:
            return (level, None)
    
    # Pattern: "High Court order reversed/set aside"
    match = re.search(r"(?P<court>\w+(?:\s+court)?)\s+(?:order|judgment)\s+(?:reversed|set aside)", text_lower)
    if match:
        court_name = match.group("court").strip()
        level = get_court_level(court_name)
        if level != CourtLevel.UNKNOWN:
            return (level, None)
    
    return (None, None)


def detect_reversal_keywords(judgment_text: str) -> bool:
    """
    Detect whether judgment contains reversal/modification keywords.
    
    Used to flag cases that may be overturns of lower court decisions.
    
    Args:
        judgment_text: Judgment text
    
    Returns:
        True if reversal patterns found, False otherwise
    """
    if not judgment_text:
        return False
    
    text_lower = judgment_text.lower()
    for pattern in REVERSAL_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    
    return False


def is_lower_court_case(court_level: CourtLevel) -> bool:
    """Check if court level is lower court tier."""
    return court_level in (CourtLevel.LOWER_COURTS,)


def is_upper_court_case(court_level: CourtLevel) -> bool:
    """Check if court level is upper court tier (High Court or Supreme Court)."""
    return court_level in (CourtLevel.HIGH_COURT, CourtLevel.SUPREME_COURT)


def get_court_hierarchy_filter(include_levels: list[CourtLevel]) -> dict:
    """
    Generate Qdrant filter for specific court levels.
    
    Args:
        include_levels: List of CourtLevel enums to include
    
    Returns:
        Qdrant filter dict for use in search operations
    
    Example:
        >>> get_court_hierarchy_filter([CourtLevel.HIGH_COURT, CourtLevel.SUPREME_COURT])
        {'court_level': {'in': [2, 1]}}
    """
    if not include_levels:
        return {}
    
    level_values = [level.value for level in include_levels]
    return {"court_level": {"in": level_values}}


def get_all_courts_for_level(level: CourtLevel) -> list[str]:
    """
    Get all court names mapped to a specific level.
    
    Args:
        level: CourtLevel to query
    
    Returns:
        List of court names at that level
    """
    return [court for court, l in COURT_HIERARCHY_MAP.items() if l == level]
