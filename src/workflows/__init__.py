"""
Workflow modules for Legal AI Assistant.

Contains LangGraph-based chat workflow only.
All document ingestion, indexing, and entity resolution workflows
have been moved to pipelines/ directory.

Submodules:
    - chat: LangGraph workflow for multi-agent conversation
"""

from .chat import build_graph, GraphState

__all__ = [
    "build_graph",
    "GraphState",
]
