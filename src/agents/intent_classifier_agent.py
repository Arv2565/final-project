import json
from typing import Dict, Any

from src.models import GraphState, IntentClassifierOutput, IntentType, ExtractedEntities
from src.config import get_openai_client, get_llm_config
from src.prompts.intent_classifier_agent import INTENT_CLASSIFIER_SYSTEM_PROMPT


class IntentClassifierAgent:
    """Classifies user intent and extracts legal entities.
    
    This agent takes the cleaned query from QueryRouterAgent and:
    1. Classifies the user's intent (procedure, law explanation, case reference, etc.)
    2. Extracts relevant entities (jurisdiction, topic, time frame)
    """

    def __init__(self) -> None:
        self.client = get_openai_client()
        self.config = get_llm_config()

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """Classify intent and extract entities from cleaned query.
        
        Args:
            state: GraphState containing 'router_output' from QueryRouterAgent
            
        Returns:
            Dict with 'classifier_output' field containing IntentClassifierOutput
            
        Raises:
            ValueError: If router_output is missing from state
        """
        router_output = state.get("router_output")
        if not router_output:
            raise ValueError("GraphState missing 'router_output' for IntentClassifierAgent")

        cleaned_query = router_output.cleaned_query
        metadata = router_output.metadata

        # Build user prompt with context from router
        user_prompt = f"Query: {cleaned_query}\n\n"
        if metadata.language and metadata.language != "en":
            user_prompt += f"(Originally in: {metadata.language})\n"
        user_prompt += "Classify the intent and extract entities."

        # Single LLM call with strict JSON mode
        response = self.client.chat.completions.create(
            model=self.config.writer_model,
            temperature=self.config.temperature_writer,
            response_format={"type": "json_object"},  # Enforce JSON output
            messages=[
                {"role": "system", "content": INTENT_CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        # Parse JSON response
        content = response.choices[0].message.content or "{}"
        try:
            result = json.loads(content)
            
            # Construct Pydantic models for validation
            entities = ExtractedEntities(**result.get("entities", {}))
            
            # Map intent string to enum (with fallback)
            intent_str = result.get("intent", "general_question")
            try:
                intent = IntentType(intent_str)
            except ValueError:
                # Invalid intent string, default to general_question
                intent = IntentType.GENERAL_QUESTION
            
            classifier_output = IntentClassifierOutput(
                intent=intent,
                entities=entities
            )
            
            # Return state update
            return {"classifier_output": classifier_output}
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
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
