from langgraph.graph import StateGraph, START, END

from src.workflows.chat.schema import GraphState
from src.nodes.research_node import research_node
from src.nodes.writer_node import writer_node


def build_graph():
    """Build and compile the LangGraph workflow.

    Flow:
        START -> research -> writer -> END
    """
    workflow = StateGraph(GraphState)

    # Register nodes
    workflow.add_node("research", research_node)
    workflow.add_node("writer", writer_node)

    # Wire edges
    workflow.add_edge(START, "research")
    workflow.add_edge("research", "writer")
    workflow.add_edge("writer", END)

    # Compile into an executable graph
    return workflow.compile()
