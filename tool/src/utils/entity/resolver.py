"""Entity resolution and deduplication for legal documents.

Provides type-specific matching rules to resolve duplicate entities:
  - Sections: Match by statute + number (e.g., "Section 420" vs "Sec 420" vs "IPC 420")
  - Cases: Match by year + court + reporter + page
  - Acts/Statutes: Match by abbreviation or canonical name
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging

from src.utils.entity.parser import (
    SectionReference, CaseCitation, StatuteReference,
    SectionParser, CaseCitationParser, StatuteParser
)

logger = logging.getLogger(__name__)


@dataclass
class EntityCluster:
    """Represents a group of equivalent entities."""
    canonical_id: str  # Chosen canonical ID for cluster
    display_name: str  # Canonical display name
    entity_type: str  # 'Section', 'Case', 'Statute', etc.
    variants: List[str] = field(default_factory=list)  # All variant names found
    confidence: float = 0.0  # Confidence of canonicalization
    metadata: Dict = field(default_factory=dict)  # Type-specific metadata


class EntityResolver:
    """Resolve duplicate legal entities using type-specific matching."""

    def __init__(self, strict_mode: bool = False):
        """Initialize resolver.
        
        Args:
            strict_mode: If True, only create clusters for high-confidence matches.
                        If False, use fuzzy matching as fallback.
        """
        self.strict_mode = strict_mode
        self.section_clusters: Dict[str, EntityCluster] = {}  # canonical_id -> cluster
        self.case_clusters: Dict[str, EntityCluster] = {}
        self.statute_clusters: Dict[str, EntityCluster] = {}
        self.entity_to_cluster: Dict[str, str] = {}  # entity_name -> canonical_id
        
        self.section_parser = SectionParser()
        self.case_parser = CaseCitationParser()
        self.statute_parser = StatuteParser()

    def resolve_section(self, text: str, statute: Optional[str] = None) -> Optional[str]:
        """Resolve section reference to canonical ID.
        
        Args:
            text: Text containing section reference (e.g., "Section 420 IPC")
            statute: Optional statute context
            
        Returns:
            Canonical ID (e.g., "IPC:Section:420") or None if unresolvable
        """
        # Try structured parsing first
        parsed = self.section_parser.parse(text, statute)
        if parsed and parsed.confidence >= 0.85:
            # Check if we've already seen this canonical ID
            if parsed.canonical_id in self.section_clusters:
                cluster = self.section_clusters[parsed.canonical_id]
                cluster.variants.append(text)
                self.entity_to_cluster[text] = parsed.canonical_id
                return parsed.canonical_id
            else:
                # Create new cluster
                cluster = EntityCluster(
                    canonical_id=parsed.canonical_id,
                    display_name=parsed.display_name,
                    entity_type='Section',
                    variants=[text],
                    confidence=parsed.confidence,
                    metadata={
                        'statute': parsed.statute,
                        'section_number': parsed.section_number,
                        'subsection': parsed.subsection,
                        'clause': parsed.clause,
                    }
                )
                self.section_clusters[parsed.canonical_id] = cluster
                self.entity_to_cluster[text] = parsed.canonical_id
                return parsed.canonical_id

        # Fallback to fuzzy matching if not in strict mode
        if not self.strict_mode:
            return self._fuzzy_match_section(text, statute)

        return None

    def resolve_case(self, text: str) -> Optional[str]:
        """Resolve case citation to canonical ID.
        
        Args:
            text: Text containing case citation
            
        Returns:
            Canonical ID (e.g., "AIR_1970_SC_1876") or None if unresolvable
        """
        # Try structured parsing
        parsed = self.case_parser.parse(text)
        if parsed and parsed.confidence >= 0.85:
            # Check for existing cluster
            if parsed.canonical_id in self.case_clusters:
                cluster = self.case_clusters[parsed.canonical_id]
                cluster.variants.append(text)
                self.entity_to_cluster[text] = parsed.canonical_id
                return parsed.canonical_id
            else:
                # Create new cluster
                cluster = EntityCluster(
                    canonical_id=parsed.canonical_id,
                    display_name=parsed.display_name,
                    entity_type='Case',
                    variants=[text],
                    confidence=parsed.confidence,
                    metadata={
                        'case_name': parsed.case_name,
                        'year': parsed.year,
                        'reporter': parsed.primary_reporter.value,
                        'court': parsed.court.value,
                        'page': parsed.primary_report_page,
                        'secondary_reports': [
                            (r.value, y, p) for r, y, p in parsed.secondary_reports
                        ]
                    }
                )
                self.case_clusters[parsed.canonical_id] = cluster
                self.entity_to_cluster[text] = parsed.canonical_id
                return parsed.canonical_id

        # Fallback to fuzzy matching
        if not self.strict_mode:
            return self._fuzzy_match_case(text)

        return None

    def resolve_statute(self, text: str) -> Optional[str]:
        """Resolve statute reference to canonical ID.
        
        Args:
            text: Text containing statute reference
            
        Returns:
            Canonical ID (e.g., "IPC:1860") or None if unresolvable
        """
        # Try structured parsing
        parsed = self.statute_parser.parse(text)
        if parsed and parsed.confidence >= 0.85:
            # Check for existing cluster
            if parsed.canonical_id in self.statute_clusters:
                cluster = self.statute_clusters[parsed.canonical_id]
                cluster.variants.append(text)
                self.entity_to_cluster[text] = parsed.canonical_id
                return parsed.canonical_id
            else:
                # Create new cluster
                cluster = EntityCluster(
                    canonical_id=parsed.canonical_id,
                    display_name=parsed.name,
                    entity_type='Statute',
                    variants=[text],
                    confidence=parsed.confidence,
                    metadata={
                        'abbreviation': parsed.abbreviation,
                        'year': parsed.year,
                    }
                )
                self.statute_clusters[parsed.canonical_id] = cluster
                self.entity_to_cluster[text] = parsed.canonical_id
                return parsed.canonical_id

        # Fallback to fuzzy matching
        if not self.strict_mode:
            return self._fuzzy_match_statute(text)

        return None

    def _fuzzy_match_section(self, text: str, statute: Optional[str] = None) -> Optional[str]:
        """Fuzzy match section reference as fallback.
        
        Uses similarity matching on normalized names and returns existing
        canonical ID if match found, else None.
        """
        norm_text = self._normalize_text(text)
        
        # Try to match against existing section clusters
        for canonical_id, cluster in self.section_clusters.items():
            for variant in cluster.variants:
                norm_variant = self._normalize_text(variant)
                similarity = difflib.SequenceMatcher(a=norm_text, b=norm_variant).ratio()
                
                # Lower threshold for fuzzy matching (0.80 vs 0.85)
                if similarity >= 0.80:
                    logger.debug(f"Fuzzy matched section: {text} -> {canonical_id} (sim={similarity:.2f})")
                    cluster.variants.append(text)
                    self.entity_to_cluster[text] = canonical_id
                    return canonical_id

        return None

    def _fuzzy_match_case(self, text: str) -> Optional[str]:
        """Fuzzy match case citation as fallback."""
        norm_text = self._normalize_text(text)
        
        for canonical_id, cluster in self.case_clusters.items():
            for variant in cluster.variants:
                norm_variant = self._normalize_text(variant)
                similarity = difflib.SequenceMatcher(a=norm_text, b=norm_variant).ratio()
                
                if similarity >= 0.80:
                    logger.debug(f"Fuzzy matched case: {text} -> {canonical_id} (sim={similarity:.2f})")
                    cluster.variants.append(text)
                    self.entity_to_cluster[text] = canonical_id
                    return canonical_id

        return None

    def _fuzzy_match_statute(self, text: str) -> Optional[str]:
        """Fuzzy match statute reference as fallback."""
        norm_text = self._normalize_text(text)
        
        for canonical_id, cluster in self.statute_clusters.items():
            for variant in cluster.variants:
                norm_variant = self._normalize_text(variant)
                similarity = difflib.SequenceMatcher(a=norm_text, b=norm_variant).ratio()
                
                if similarity >= 0.80:
                    logger.debug(f"Fuzzy matched statute: {text} -> {canonical_id} (sim={similarity:.2f})")
                    cluster.variants.append(text)
                    self.entity_to_cluster[text] = canonical_id
                    return canonical_id

        return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        import unicodedata
        import re
        
        # Unicode normalization
        text = unicodedata.normalize("NFKC", text)
        # Remove punctuation and collapse whitespace
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip().lower()
        return text

    def get_canonical_id(self, entity_text: str, entity_type: Optional[str] = None) -> Optional[str]:
        """Get canonical ID for any entity text.
        
        Args:
            entity_text: The entity text to resolve
            entity_type: Optional hint ('Section', 'Case', 'Statute'). If not provided, tries all types.
            
        Returns:
            Canonical ID or None if unresolvable
        """
        # Check if already resolved
        if entity_text in self.entity_to_cluster:
            return self.entity_to_cluster[entity_text]

        # Try type-specific resolution
        if entity_type == 'Section':
            return self.resolve_section(entity_text)
        elif entity_type == 'Case':
            return self.resolve_case(entity_text)
        elif entity_type == 'Statute':
            return self.resolve_statute(entity_text)
        else:
            # Try all types (heuristic: cases often have "v", statutes have "Act", sections have numbers)
            if ' v ' in entity_text or ' v. ' in entity_text:
                return self.resolve_case(entity_text)
            elif 'Act' in entity_text or 'Code' in entity_text or 'Rule' in entity_text:
                return self.resolve_statute(entity_text)
            else:
                # Try sections
                result = self.resolve_section(entity_text)
                if result:
                    return result
                # Fallback to statute
                return self.resolve_statute(entity_text)

    def get_cluster_info(self, canonical_id: str) -> Optional[EntityCluster]:
        """Get cluster information for a canonical ID."""
        if canonical_id in self.section_clusters:
            return self.section_clusters[canonical_id]
        elif canonical_id in self.case_clusters:
            return self.case_clusters[canonical_id]
        elif canonical_id in self.statute_clusters:
            return self.statute_clusters[canonical_id]
        return None

    def get_all_variants(self, canonical_id: str) -> List[str]:
        """Get all known variants for a canonical ID."""
        cluster = self.get_cluster_info(canonical_id)
        if cluster:
            return cluster.variants
        return []

    def stats(self) -> Dict[str, int]:
        """Get resolution statistics."""
        return {
            'section_clusters': len(self.section_clusters),
            'case_clusters': len(self.case_clusters),
            'statute_clusters': len(self.statute_clusters),
            'total_clusters': len(self.section_clusters) + len(self.case_clusters) + len(self.statute_clusters),
            'total_variants': len(self.entity_to_cluster),
            'strict_mode': self.strict_mode,
        }
