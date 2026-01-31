"""
Workflow modules for Legal AI Assistant.

Contains LangGraph-based chat workflow only.
All document ingestion, indexing, and entity resolution workflows
have been moved to pipelines/ directory.

Submodules:
    - chat: LangGraph workflow for multi-agent conversation
"""

<<<<<<< HEAD
try:
    from .chat import build_graph, GraphState
    __all__ = [
        "build_graph",
        "GraphState",
    ]
except ImportError:
    # Allow importing other modules even if chat dependencies (langgraph) are missing/broken
    __all__ = []
=======
from .chat import build_graph, GraphState

__all__ = [
    "build_graph",
    "GraphState",
]
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
