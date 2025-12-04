"""
Agents module for legal document processing and query routing.
"""

from .query_router_agent import QueryRouterAgent
from .intent_classifier_agent import IntentClassifierAgent

# Lazy import for LegalDocumentKnowledgeExtractor to avoid dependency issues
def _get_legal_knowledge_extractor():
    from .legal_knowledge_extractor import LegalDocumentKnowledgeExtractor
    return LegalDocumentKnowledgeExtractor

__all__ = [
    'QueryRouterAgent',
    'IntentClassifierAgent',
]