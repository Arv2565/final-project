from typing import Dict, Any

from src.workflows.chat.schema import GraphState
from src.agents.research_agent import ResearchAgent


_research_agent = ResearchAgent()


def research_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to ResearchAgent."""
    return _research_agent(state)
