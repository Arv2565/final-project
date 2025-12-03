from typing import Dict, Any

from src.workflows.chat.schema import GraphState
from src.agents.writer_agent import WriterAgent


_writer_agent = WriterAgent()


def writer_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to WriterAgent."""
    return _writer_agent(state)
