"""
Ambiguity Remover module - exports and initialization.

Quick imports:
    from src.agents.ambiguity_remover import AmbiguityRemover, ClarificationRequest
    from src.nodes.ambiguity_remover_node import ambiguity_remover_node
"""

from src.agents.ambiguity_remover import (
    AmbiguityRemover,
    ClarificationRequest,
    ClarificationResult,
)

__all__ = [
    "AmbiguityRemover",
    "ClarificationRequest",
    "ClarificationResult",
]
