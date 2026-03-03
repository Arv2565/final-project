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
    civil_procedural_guidance_node, 
    criminal_procedural_guidance_node
)
from src.nodes.general_chat_node import general_chat_node
from src.nodes.ambiguity_remover_node import ambiguity_remover_runnable, set_ambiguity_remover
from src.agents.ambiguity_remover import AmbiguityRemover

# Document Generation Nodes
from src.nodes.doc_gen_template_selection import doc_gen_template_selection_node
from src.nodes.doc_gen_placeholder_extraction import doc_gen_placeholder_extraction_node
from src.nodes.doc_gen_clarification import doc_gen_clarification_node
# Replaced doc_gen_generation with granular nodes
from src.nodes.doc_gen_document_creation import doc_gen_document_creation_node
from src.nodes.doc_gen_procedure_generation import doc_gen_procedure_generation_node

from src.nodes.placeholder_node import placeholder_node


def route_from_orchestrator(state: GraphState) -> Literal["ambiguity_remover", "fact_structuring", "procedural_guidance_civil", "procedural_guidance_criminal", "draft_builder", "educational_layer", "case_retriever", "comparative_module", "doc_gen_template_selection", "general_chat", "__end__"]:
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

    if state.get("ambiguity_remover_scope") and state.get("needs_clarification"):
        return "ambiguity_remover"

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
        7: "doc_gen_template_selection", # Explicit doc gen
        0: "general_chat",
    }
    
    target = agent_routing.get(agent_number, END)
    
    # Remap draft_builder/3 to doc_gen_template_selection if used
    if target == "draft_builder" or target == "document_generation":
         return "doc_gen_template_selection"
         
    return target


def route_from_fact_structuring(state: GraphState) -> Literal["ambiguity_remover", "statute_matching", "__end__"]:
    """Route from fact_structuring, checking for ambiguity or clarification."""
    # Check if agent flagged ambiguity needing removal
    if state.get("ambiguity_remover_scope"):
        return "ambiguity_remover"
    
    # Check if clarification is pending
    if state.get("pending_clarification"):
        return END
    
    return "statute_matching"


def route_from_ambiguity_remover(state: GraphState) -> Literal["orchestrator", "statute_matching", "__end__"]:
    """Route from ambiguity_remover back to pipeline or halt."""
    # If clarification was generated, halt for user input
    if state.get("pending_clarification"):
        return END
    
    next_node = state.get("ambiguity_remover_next", "statute_matching")
    if next_node == "orchestrator":
        return "orchestrator"
    return "statute_matching"


def route_from_doc_gen_clarification(state: GraphState) -> Literal["doc_gen_document_creation", "__end__"]:
    """
    Route from clarification check.
    If pending clarification, STOP (return END) to wait for user input.
    Else, proceed to document creation.
    """
    if state.get("pending_clarification"):
        return END
    return "doc_gen_document_creation"


def route_from_general_chat(state: GraphState) -> Literal["orchestrator", "__end__"]:
    """Route from general_chat.

    By default we end the current graph run. If caller explicitly sets
    loop_to_orchestrator=True, route back to orchestrator.
    """
    if state.get("loop_to_orchestrator"):
        return "orchestrator"
    return END


def build_graph(llm_provider=None):
    """Build and compile the LangGraph workflow for legal query processing.

    Flow:
        START → query_router → intent_classifier → orchestrator
        orchestrator --(cond)--> ...
        
    Args:
        llm_provider: Optional LLM provider for AmbiguityRemover. 
    
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
    workflow.add_node("ambiguity_remover", ambiguity_remover_runnable)
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

    # Register Placeholder nodes for unimplemented agents
    workflow.add_node("draft_builder", placeholder_node) # Can be removed if completely replaced, but kept for safety
    workflow.add_node("educational_layer", placeholder_node)
    workflow.add_node("case_retriever", placeholder_node)
    workflow.add_node("comparative_module", placeholder_node)
    
    # Register Document Generation nodes (Broken down)
    workflow.add_node("doc_gen_template_selection", doc_gen_template_selection_node)
    workflow.add_node("doc_gen_placeholder_extraction", doc_gen_placeholder_extraction_node)
    workflow.add_node("doc_gen_clarification", doc_gen_clarification_node)
    workflow.add_node("doc_gen_document_creation", doc_gen_document_creation_node)
    workflow.add_node("doc_gen_procedure_generation", doc_gen_procedure_generation_node)

    # Wire edges: Main Pipeline
    workflow.add_edge(START, "query_router")
    workflow.add_edge("query_router", "orchestrator")
    
    # Conditional Edge from Orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "ambiguity_remover": "ambiguity_remover",
            "fact_structuring": "fact_structuring",
            "procedural_guidance_civil": "procedural_guidance_civil",
            "procedural_guidance_criminal": "procedural_guidance_criminal",
            "draft_builder": "doc_gen_template_selection", # Mapped
            "educational_layer": END,
            "case_retriever": END,
            "comparative_module": END,
            "doc_gen_template_selection": "doc_gen_template_selection",
            "general_chat": "general_chat",
            END: END
        }
    )
    
    # Wire edges: Activity to Law Pipeline
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
            "orchestrator": "orchestrator",
            "statute_matching": "statute_matching",
            END: END
        }
    )

    workflow.add_edge("statute_matching", "rule_matching")
    workflow.add_edge("rule_matching", "risk_assessment")
    workflow.add_edge("risk_assessment", "evidence_linking")
    workflow.add_edge("evidence_linking", "response_generation")
    
    # Document Generation Sub-graph Wiring
    workflow.add_edge("doc_gen_template_selection", "doc_gen_placeholder_extraction")
    workflow.add_edge("doc_gen_placeholder_extraction", "doc_gen_clarification")
    
    workflow.add_conditional_edges(
        "doc_gen_clarification",
        route_from_doc_gen_clarification,
        {
            "doc_gen_document_creation": "doc_gen_document_creation",
            END: END
        }
    )
    workflow.add_edge("doc_gen_document_creation", "doc_gen_procedure_generation")
    workflow.add_edge("doc_gen_procedure_generation", END)

    # Route all terminal nodes directly to END
    workflow.add_edge("response_generation", END)
    workflow.add_edge("procedural_guidance_civil", END)
    workflow.add_edge("procedural_guidance_criminal", END)
    workflow.add_conditional_edges(
        "general_chat",
        route_from_general_chat,
        {
            "orchestrator": "orchestrator",
            END: END,
        }
    )
    # Draft builder is not used if we map to doc_gen_template_selection, but for graph completeness:
    workflow.add_edge("draft_builder", END)
    workflow.add_edge("educational_layer", END)
    workflow.add_edge("case_retriever", END)
    workflow.add_edge("comparative_module", END)

    # Compile into an executable graph
    return workflow.compile()
