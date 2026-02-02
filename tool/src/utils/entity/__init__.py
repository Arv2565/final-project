"""
Entity utilities for entity resolution and parsing.
"""

from .resolver import EntityResolver
from .parser import LegalEntityParser, SectionReference, CaseCitation, StatuteReference

__all__ = [
    "EntityResolver",
    "LegalEntityParser",
    "SectionReference",
    "CaseCitation",
    "StatuteReference",
]
