from langgraph.graph import StateGraph, START, END

from src.models import GraphState
from src.nodes.query_router_node import query_router_node
from src.nodes.intent_classifier_node import intent_classifier_node


def build_graph():
    """Build and compile the LangGraph workflow for legal query processing.

    Flow:
        START → query_router → intent_classifier → END
        
    State transitions:
        1. query_router: Takes 'user_query' → produces 'router_output'
           - Normalizes and cleans the query
           - Translates to English if needed
           - Extracts basic metadata (language, PII, legal question flag)
           
        2. intent_classifier: Takes 'router_output' → produces 'classifier_output'
           - Classifies user intent (procedure, law explanation, case, etc.)
           - Extracts legal entities (jurisdiction, topic, time frame)
    
    Returns:
        Compiled LangGraph workflow ready for invocation
    """
    workflow = StateGraph(GraphState)

    # Register nodes for legal query processing pipeline
    workflow.add_node("query_router", query_router_node)
    workflow.add_node("intent_classifier", intent_classifier_node)

    # Wire edges: linear flow from router to classifier
    workflow.add_edge(START, "query_router")
    workflow.add_edge("query_router", "intent_classifier")
    workflow.add_edge("intent_classifier", END)

    # Compile into an executable graph
    return workflow.compile()
