from langgraph.graph import StateGraph, START, END
from src.models import GraphState

# Import Nodes
from src.workflows.procedural.nodes import (
    timeline_constraint_node,
    checklist_generator_node,
    responsible_actor_node,
    estimated_effort_node,
    procedural_response_node
)

from typing import Literal

def route_from_timeline(state: GraphState) -> Literal["checklist_generator", "__end__"]:
    """Route from timeline, checking for clarification."""
    if state.get("pending_clarification"):
        return END
    return "checklist_generator"

def build_procedural_graph():
    """Build and compile the Procedural Guidance subgraph.
    
    Flow:
        START → timeline_constraint → checklist_generator → 
        responsible_actor → estimated_effort → procedural_response → END
    """
    workflow = StateGraph(GraphState)
    
    # Register Nodes
    workflow.add_node("timeline_constraint", timeline_constraint_node)
    workflow.add_node("checklist_generator", checklist_generator_node)
    workflow.add_node("responsible_actor", responsible_actor_node)
    workflow.add_node("estimated_effort", estimated_effort_node)
    workflow.add_node("procedural_response", procedural_response_node)
    
    # Wire Edges (Linear Flow with Check)
    workflow.add_edge(START, "timeline_constraint")
    
    workflow.add_conditional_edges(
        "timeline_constraint",
        route_from_timeline,
        {
            "checklist_generator": "checklist_generator",
            END: END
        }
    )
    
    # workflow.add_edge("timeline_constraint", "checklist_generator") # Replaced
    workflow.add_edge("checklist_generator", "responsible_actor")
    workflow.add_edge("responsible_actor", "estimated_effort")
    workflow.add_edge("estimated_effort", "procedural_response")
    workflow.add_edge("procedural_response", END)
    
    return workflow.compile()
