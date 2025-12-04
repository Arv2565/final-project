from typing import TypedDict, NotRequired
from src.models.query_router import QueryRouterOutput
from src.models.intent_classifier import IntentClassifierOutput


class GraphState(TypedDict, total=False):
    """State for legal query processing workflow.
    
    Flow:
        user_query → QueryRouterAgent → router_output
        router_output → IntentClassifierAgent → classifier_output
    
    Fields:
        user_query: Original input from the user
        router_output: Cleaned query and metadata from QueryRouterAgent
        classifier_output: Intent and entities from IntentClassifierAgent
    """
    
    user_query: str
    router_output: NotRequired[QueryRouterOutput]
    classifier_output: NotRequired[IntentClassifierOutput]
