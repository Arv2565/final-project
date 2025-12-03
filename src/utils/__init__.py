"""
Backward compatibility shim for old utils imports.

This module provides backward compatibility for old import paths.
All actual implementations have been moved to subdirectories.

DEPRECATED: Use new imports directly from src/utils/entity/, src/utils/pdf/, src/utils/graph/
"""

import warnings

# Import from new locations and re-export for backward compatibility
from src.utils.entity.resolver import EntityResolver as EntityResolver
from src.utils.entity.parser import (
    LegalEntityParser as LegalEntityParser,
    SectionReference as SectionReference,
    CaseCitation as CaseCitation,
    StatuteReference as StatuteReference,
)
from src.utils.pdf.extractor import PDFTextExtractor as PDFTextExtractor
from src.utils.graph.vector_retrieval import (
    VectorSearch as VectorSearch,
    VectorRetrievalService as VectorRetrievalService,
)
from src.utils.graph.cypher import CypherBuilder as CypherBuilder

# Cache manager (kept in main utils)
from src.utils.cache_manager import *

__all__ = [
    "EntityResolver",
    "LegalEntityParser",
    "SectionReference",
    "CaseCitation",
    "StatuteReference",
    "PDFTextExtractor",
    "VectorSearch",
    "VectorRetrievalService",
    "CypherBuilder",
]

def __getattr__(name):
    """Provide deprecation warnings for old imports."""
    warnings.warn(
        f"Importing {name} from src.utils is deprecated. "
        f"Use new module structure instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return None
