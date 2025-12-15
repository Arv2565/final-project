from typing import Dict, Any, List

from src.models import GraphState, IntentClassifierOutput, IntentType, ExtractedEntities
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.intent_classifier_agent import INTENT_CLASSIFIER_SYSTEM_PROMPT


class IntentClassifierAgent:
    """Classifies user intent and extracts legal entities.
    
    This agent takes the cleaned query from QueryRouterAgent and:
    1. Classifies the user's intent (procedure, law explanation, case reference, etc.)
    2. Extracts relevant entities (jurisdiction, topic, time frame)
    """

    def __init__(self) -> None:
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=IntentClassifierOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Classify intent and extract entities from cleaned query.
        
        Args:
            state: GraphState containing 'router_output' from QueryRouterAgent
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'classifier_output' field containing IntentClassifierOutput
            
        Raises:
            ValueError: If router_output is missing from state
        """
        print("\n" + "="*80)
        print("🔍 INTENT CLASSIFIER AGENT")
        print("="*80)
        
        router_output = state.get("router_output")
        if not router_output:
            raise ValueError("GraphState missing 'router_output' for IntentClassifierAgent")

        cleaned_query = router_output.cleaned_query
        metadata = router_output.metadata
        
        print(f"\n📥 Input State:")
        import json
        print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))

        # Build user prompt with context from router
        user_prompt = f"Query: {cleaned_query}\n\n"
        if metadata.language and metadata.language != "en":
            user_prompt += f"(Originally in: {metadata.language})\n"
        user_prompt += "Classify the intent and extract entities."

        try:
            # LangChain handles structured output binding and validation
            classifier_output = self.llm.invoke(
                [
                    {"role": "system", "content": INTENT_CLASSIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Classifier Output:")
            print(f"   Intent: {classifier_output.intent.value}")
            print(f"   Jurisdiction: {classifier_output.entities.jurisdiction}")
            print(f"   Topic: {classifier_output.entities.topic}")
            print(f"   Time Frame: {classifier_output.entities.time_frame}")
            
            result_state = {**state, "classifier_output": classifier_output}
            print(f"\n📤 Full Graph State Update:")
            print(json.dumps({k: str(v) for k, v in result_state.items()}, indent=2))
            
            return {"classifier_output": classifier_output}
            
        except Exception as e:
            print(f"\n⚠️  Classifier failed, using fallback: {str(e)[:100]}")
            # Fallback: Default to general question with no entities
            fallback_output = IntentClassifierOutput(
                intent=IntentType.GENERAL_QUESTION,
                entities=ExtractedEntities(
                    jurisdiction=None,
                    topic=None,
                    time_frame=None
                )
            )
            return {"classifier_output": fallback_output}
