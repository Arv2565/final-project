"""
Chat/LangGraph Workflow.

Orchestrates the LangGraph-based conversational workflow for the Legal AI Assistant.

Architecture:
    question → research_node → research_notes
                    ↓
              writer_node → answer → END

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
