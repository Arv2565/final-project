from langgraph.graph import StateGraph, START, END
from typing import Literal

from src.models import GraphState, AgentType
from src.nodes.query_router_node import query_router_node
from src.nodes.orchestrator_node import orchestrator_node
from src.nodes.fact_structuring_node import fact_structuring_node
from src.nodes.statute_matching_node import statute_matching_node
from src.nodes.rule_matching_node import rule_matching_node
from src.nodes.risk_assessment_node import risk_assessment_node
from src.nodes.response_generation_node import response_generation_node
from src.nodes.evidence_linking_node import evidence_linking_node


def route_from_orchestrator(state: GraphState) -> Literal["fact_structuring", "procedural_guidance", "draft_builder", "educational_layer", "case_retriever", "comparative_module", "__end__"]:
    """Route based on the first agent number in the orchestrator plan.
    
    Agent mapping:
        1 → fact_structuring (Activity-to-Law pipeline)
        2 → procedural_guidance
        3 → draft_builder
        4 → educational_layer
        5 → case_retriever
        6 → comparative_module
    """
    plan_data = state.get("orchestrator_plan")
    
    if not plan_data:
        return END

    # Handle both new dict format (with steps key) and old list format (just steps)
    if isinstance(plan_data, dict):
        steps = plan_data.get("steps", [])
    elif isinstance(plan_data, list):
        steps = plan_data
    else:
        return END

    if not steps:
        return END
        
    # Check the first step in the plan
    first_step = steps[0]
    
    # Handle if step is dict or object (it should be dict as we serialized it)
    if isinstance(first_step, dict):
        agent_number = first_step.get("agent_number")
    else:
        agent_number = getattr(first_step, "agent_number", None)
    
    agent_routing = {
        1: "fact_structuring",
        2: "procedural_guidance",
        3: "draft_builder",
        4: "educational_layer",
        5: "case_retriever",
        6: "comparative_module",
    }
    
    return agent_routing.get(agent_number, END)


def build_graph():
    """Build and compile the LangGraph workflow for legal query processing.

    Flow:
        START → query_router → intent_classifier → orchestrator
        orchestrator --(cond)--> fact_structuring → ... → evidence_linking → response_generation → END
        
    [...]
    """
    workflow = StateGraph(GraphState)

    # Register nodes
    workflow.add_node("query_router", query_router_node)
    workflow.add_node("orchestrator", orchestrator_node)
    
    # Register Activity to Law nodes
    workflow.add_node("fact_structuring", fact_structuring_node)
    workflow.add_node("statute_matching", statute_matching_node)
    workflow.add_node("rule_matching", rule_matching_node)
    workflow.add_node("risk_assessment", risk_assessment_node)
    workflow.add_node("evidence_linking", evidence_linking_node)
    workflow.add_node("response_generation", response_generation_node)

    # Wire edges: Main Pipeline
    workflow.add_edge(START, "query_router")
    workflow.add_edge("query_router", "orchestrator")
    
    # Conditional Edge from Orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "fact_structuring": "fact_structuring",
            END: END
        }
    )
    
    # Wire edges: Activity to Law Pipeline (Linear)
    workflow.add_edge("fact_structuring", "statute_matching")
    workflow.add_edge("statute_matching", "rule_matching")
    workflow.add_edge("rule_matching", "risk_assessment")
    workflow.add_edge("risk_assessment", "evidence_linking")
    workflow.add_edge("evidence_linking", "response_generation")
    workflow.add_edge("response_generation", END)

    # Compile into an executable graph
    return workflow.compile()
