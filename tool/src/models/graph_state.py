from typing import TypedDict, List
from typing_extensions import NotRequired
from src.models.query_router import QueryRouterOutput
from src.models.intent_classifier import IntentClassifierOutput
from src.models.activity_law import ActivityLawState
from src.models.procedural_guidance import ProceduralGuidanceState


class GraphState(TypedDict, total=False):
    """State for legal query processing workflow.
    
    Flow:
        user_query → QueryRouterAgent → router_output
        router_output → IntentClassifierAgent → classifier_output
        classifier_output → OrchestratorAgent → orchestrator_plan
        orchestrator_plan → route to specialized agents
    
    Fields:
        user_query: Original input from the user
        router_output: Cleaned query and metadata from QueryRouterAgent
        classifier_output: Intent and entities from IntentClassifierAgent
        orchestrator_plan: List of steps with numeric agent IDs (1-6) and reasoning
    """
    
    user_query: str
    router_output: NotRequired[QueryRouterOutput]
    classifier_output: NotRequired[IntentClassifierOutput]
    
    # Orchestrator output - list of dicts with:
    # - agent_number: int (1-6)
    # - reasoning: str
    orchestrator_plan: NotRequired[List[dict]]
    
    # Specialized Agent outputs
    legal_laws: NotRequired[List[str]] # ActivityToLawAgent
    procedural_advice: NotRequired[str] # ProceduralGuidanceAgent (legacy field)
    draft_document: NotRequired[str] # DraftBuilderAgent
    educational_content: NotRequired[str] # EducationalLayerAgent
    case_law: NotRequired[List[str]] # CaseRetrieverAgent
    comparison_result: NotRequired[str] # ComparativeModuleAgent
    
    # Activity to Law Workflow State
    activity_law_state: NotRequired[ActivityLawState]
    
    # Procedural Guidance Workflow State
    procedural_guidance_state: NotRequired[ProceduralGuidanceState] # Legacy/Generic
    procedural_guidance_civil_state: NotRequired[ProceduralGuidanceState]
    procedural_guidance_criminal_state: NotRequired[ProceduralGuidanceState]
    
    # Final Output
    final_response: NotRequired[str]
    generated_document_content: NotRequired[str] # Content specifically for PDF generation (before user prompts added)
    generated_document_path: NotRequired[str]
    
    # Clarification System
    clarification_history: NotRequired[List[dict]]  # List of {question: str, answer: str}
    clarification_counts: NotRequired[dict]         # Count of questions per agent: {agent_name: count}
    pending_clarification: NotRequired[dict]        # Serialized ClarificationRequest
    
    # Internal State
    active_legal_domain: NotRequired[str]           # 'civil' or 'criminal' - Explicit override for subgraphs
