"""
Chat/LangGraph Workflow.

Orchestrates the LangGraph-based conversational workflow for the Legal AI Assistant.

Architecture:
    user_query → query_router → router_output
                    ↓
                 intent_classifier → classifier_output → END

Modules:
    - builder: LangGraph workflow definition and compilation
    - schema: GraphState TypedDict for workflow state management
"""

from .builder import build_graph
from .schema import GraphState

__all__ = [
    "build_graph",
    "GraphState",
]
