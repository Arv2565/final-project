"""
Entity utilities for entity resolution and parsing.
"""

from .resolver import EntityResolver
from .parser import LegalEntityParser

__all__ = [
    "EntityResolver",
    "LegalEntityParser",
]
