from typing import TypedDict, NotRequired, List
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
    
    # Orchestrator output
    orchestrator_plan: NotRequired[List[dict]] # Serialized OrchestratorPlan steps
    
    # Specialized Agent outputs
    legal_laws: NotRequired[List[str]] # ActivityToLawAgent
    procedural_advice: NotRequired[str] # ProceduralGuidanceAgent
    draft_document: NotRequired[str] # DraftBuilderAgent
    educational_content: NotRequired[str] # EducationalLayerAgent
    case_law: NotRequired[List[str]] # CaseRetrieverAgent
    comparison_result: NotRequired[str] # ComparativeModuleAgent

