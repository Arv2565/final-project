from langgraph.graph import StateGraph, START, END
from typing import Literal, Optional

from src.models import GraphState, AgentType
from src.nodes.query_router_node import query_router_node
from src.nodes.orchestrator_node import orchestrator_node
from src.nodes.fact_structuring_node import fact_structuring_node
from src.nodes.statute_matching_node import statute_matching_node
from src.nodes.rule_matching_node import rule_matching_node
from src.nodes.risk_assessment_node import risk_assessment_node
from src.nodes.response_generation_node import response_generation_node
from src.nodes.evidence_linking_node import evidence_linking_node
from src.nodes.procedural_guidance_node import (
    procedural_guidance_node, 
    civil_procedural_guidance_node, 
    criminal_procedural_guidance_node
)
from src.nodes.general_chat_node import general_chat_node
from src.nodes.ambiguity_remover_node import ambiguity_remover_node, set_ambiguity_remover
from src.agents.ambiguity_remover import AmbiguityRemover


def route_from_orchestrator(state: GraphState) -> Literal["fact_structuring", "procedural_guidance", "draft_builder", "educational_layer", "case_retriever", "comparative_module", "general_chat", "__end__"]:
    """Route based on the next_module selected by the orchestrator.
    
    Agent mapping:
        1 → fact_structuring (Activity-to-Law pipeline)
        2 → procedural_guidance
        3 → draft_builder
        4 → educational_layer
        5 → case_retriever
        6 → comparative_module
        0 → general_chat
    """
    if state.get("pending_clarification"):
        return END

    plan_data = state.get("orchestrator_plan")
    
    if not plan_data:
        return END

    # Extract next_module from the orchestrator plan
    if isinstance(plan_data, dict):
        next_module = plan_data.get("next_module")
    else:
        return END
        
    # If next_module is None (e.g. only clarification was returned but somehow pending_clarification wasn't set?), return END
    if not next_module:
        return END

    # ... rest of logic ...
    
    # Extract agent_number from next_module
    if isinstance(next_module, dict):
        agent_number = next_module.get("agent_number")
    else:
        agent_number = getattr(next_module, "agent_number", None)
    
    if agent_number is None:
        return END
    
    # Extract legal_domain
    legal_domain = plan_data.get("legal_domain", "criminal") # Default to criminal
    
    # Map agent number to node name
    if agent_number == 2: # Procedural Guidance
        if legal_domain == "civil":
            return "procedural_guidance_civil"
        elif legal_domain == "criminal":
            return "procedural_guidance_criminal"
        elif legal_domain == "both":
            return ["procedural_guidance_civil", "procedural_guidance_criminal"]
        else:
            return "procedural_guidance_criminal" # Fallback

    agent_routing = {
        1: "fact_structuring",
        3: "draft_builder",
        4: "educational_layer",
        5: "case_retriever",
        6: "comparative_module",
        0: "general_chat",
    }
    
    return agent_routing.get(agent_number, END)


def route_from_fact_structuring(state: GraphState) -> Literal["ambiguity_remover", "statute_matching", "__end__"]:
    """Route from fact_structuring, checking for ambiguity or clarification."""
    # Check if agent flagged ambiguity needing removal
    if state.get("ambiguity_remover_scope"):
        return "ambiguity_remover"
    
    # Check if clarification is pending
    if state.get("pending_clarification"):
        return END
    
    return "statute_matching"


def route_from_ambiguity_remover(state: GraphState) -> Literal["statute_matching", "__end__"]:
    """Route from ambiguity_remover back to pipeline or halt."""
    # If clarification was generated, halt for user input
    if state.get("pending_clarification"):
        return END
    
    # Otherwise continue to next stage
    return "statute_matching"


def build_graph(llm_provider=None):
    """Build and compile the LangGraph workflow for legal query processing.

    Flow:
        START → query_router → intent_classifier → orchestrator
        orchestrator --(cond)--> fact_structuring → [ambiguity_remover] → statute_matching → ... → response_generation → END
        
    Args:
        llm_provider: Optional LLM provider for AmbiguityRemover. If not provided, 
                     AmbiguityRemover will be created with default LLM.
    
    Returns:
        Compiled workflow graph
    """
    workflow = StateGraph(GraphState)

    # Initialize AmbiguityRemover
    if llm_provider is None:
        # Import default LLM provider
        from src.config import get_llm_provider
        llm_provider = get_llm_provider()
    
    ambiguity_remover = AmbiguityRemover(llm=llm_provider)
    set_ambiguity_remover(ambiguity_remover)

    # Register nodes
    workflow.add_node("query_router", query_router_node)
    workflow.add_node("orchestrator", orchestrator_node)
    
    # Register Activity to Law nodes
    workflow.add_node("fact_structuring", fact_structuring_node)
    workflow.add_node("ambiguity_remover", ambiguity_remover_node)
    workflow.add_node("statute_matching", statute_matching_node)
    workflow.add_node("rule_matching", rule_matching_node)
    workflow.add_node("risk_assessment", risk_assessment_node)
    workflow.add_node("evidence_linking", evidence_linking_node)
    workflow.add_node("response_generation", response_generation_node)
    
    # Register Procedural Guidance nodes
    workflow.add_node("procedural_guidance_civil", civil_procedural_guidance_node)
    workflow.add_node("procedural_guidance_criminal", criminal_procedural_guidance_node)
    
    # Register General Chat node
    workflow.add_node("general_chat", general_chat_node)

    # Wire edges: Main Pipeline
    workflow.add_edge(START, "query_router")
    workflow.add_edge("query_router", "orchestrator")
    
    # Conditional Edge from Orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "fact_structuring": "fact_structuring",
            "procedural_guidance_civil": "procedural_guidance_civil",
            "procedural_guidance_criminal": "procedural_guidance_criminal",
            "draft_builder": END, # placeholders
            "educational_layer": END,
            "case_retriever": END,
            "comparative_module": END,
            "general_chat": "general_chat",
            END: END
        }
    )
    
    # Wire edges: Activity to Law Pipeline (with AmbiguityRemover integration)
    workflow.add_conditional_edges(
        "fact_structuring",
        route_from_fact_structuring,
        {
            "ambiguity_remover": "ambiguity_remover",
            "statute_matching": "statute_matching",
            END: END
        }
    )
    
    # Route from AmbiguityRemover
    workflow.add_conditional_edges(
        "ambiguity_remover",
        route_from_ambiguity_remover,
        {
            "statute_matching": "statute_matching",
            END: END
        }
    )

    workflow.add_edge("statute_matching", "rule_matching")
    workflow.add_edge("rule_matching", "risk_assessment")
    workflow.add_edge("risk_assessment", "evidence_linking")
    workflow.add_edge("evidence_linking", "response_generation")
    workflow.add_edge("response_generation", END)
    
    # Wire procedural nodes to end
    workflow.add_edge("procedural_guidance_civil", END)
    workflow.add_edge("procedural_guidance_criminal", END)
    
    # Wire edge: General Chat to end
    workflow.add_edge("general_chat", END)

    # Compile into an executable graph
    return workflow.compile()
