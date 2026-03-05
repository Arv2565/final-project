from typing import Dict, Any, List

from src.models import GraphState, OrchestratorPlan
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.orchestrator_agent import ORCHESTRATOR_SYSTEM_PROMPT


class OrchestratorAgent:
    """Central Brain that routes queries to specialized agents.
    
    Decides which agents to call based on intent and entities.
    """

    def __init__(self) -> None:
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=OrchestratorPlan,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Select the next appropriate module for the query.
        
        Args:
            state: GraphState containing 'router_output'
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'orchestrator_plan' field containing next_module
        """
        print("\n" + "="*80)
        print("🎯 ORCHESTRATOR AGENT (Single Step)")
        print("="*80)
        
        router_output = state.get("router_output")
        
        if not router_output:
            raise ValueError("GraphState missing 'router_output' for OrchestratorAgent")

        cleaned_query = router_output.cleaned_query
        metadata = router_output.metadata

        language_map = {
            "en": "English",
            "hi": "Hindi",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
            "ja": "Japanese",
            "zh": "Chinese",
            "ta": "Tamil",
            "te": "Telugu",
            "kn": "Kannada",
            "ml": "Malayalam",
        }
        original_language_code = (metadata.original_language or metadata.language or "en") if metadata else "en"
        response_language_name = language_map.get(original_language_code, "English")

        print(f"\n📥 Input State:")
        import json
        # Safe printing of state (excluding large objects if any)
        print(json.dumps({k: str(v) for k, v in state.items() if k != "messages"}, indent=2))

        # Clarification Logic
        clarification_counts = state.get("clarification_counts", {})
        current_count = clarification_counts.get("orchestrator", 0)
        MAX_CLARIFICATION = 3 
        
        clarification_history = state.get("clarification_history", [])
        chat_context = (state.get("chat_context") or "").strip()
        
        # Build user prompt
        user_prompt = f"Query: {cleaned_query}\n\n"
        if metadata.language and metadata.language != "en":
            user_prompt += f"(Originally in: {metadata.language})\n"
        
        if chat_context:
            user_prompt += f"\n{chat_context}\n"
            
        if clarification_history:
            user_prompt += "\nPrevious Clarifications:\n"
            for item in clarification_history:
                user_prompt += f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}\n"
        
        user_prompt += """
        Determine the single best next module (agent number 0-6) to handle this query.
        """
        
        if current_count < MAX_CLARIFICATION:
            user_prompt += "\nIf the query is too vague to select a single module, or missing critical info, you MAY request clarification. Set 'clarification' field and leave 'next_module' empty."
            user_prompt += (
                f"\nIf clarification is needed, write the clarification question and reason in {response_language_name} "
                f"(language code: {original_language_code})."
            )
        else:
            user_prompt += "\nYou have reached the limit for clarifications. You MUST make a best-guess selection."

        try:
            plan = self.llm.invoke(
                [
                    {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Orchestrator Output:")
            if plan.clarification:
                print(f"   Requesting Clarification: {plan.clarification.question}")
                serialized_plan = plan.model_dump()
                return {
                    "orchestrator_plan": serialized_plan,
                    "needs_clarification": True,
                    "ambiguity_remover_scope": "factual",
                    "ambiguity_remover_context": {
                        "agent": "orchestrator",
                        "router_metadata": metadata.model_dump() if hasattr(metadata, "model_dump") else str(metadata),
                        "orchestrator_reasoning": plan.next_module.reasoning if plan.next_module else "",
                        "agent_requested_question": plan.clarification.question,
                        "agent_requested_reason": plan.clarification.reason,
                    },
                    "current_agent": "orchestrator",
                    "ambiguity_remover_next": "orchestrator",
                }

            if plan.next_module:
                print(f"   Selected Module: {plan.next_module.agent_number}")
                print(f"   Reasoning: {plan.next_module.reasoning}")
            
            # Serialize for graph state
            serialized_plan = plan.model_dump()
            
            # We no longer generate 'classifier_output' or 'intent'
            
            result_state = {**state, "orchestrator_plan": serialized_plan}
            
            print(f"\n📤 Full Graph State Update:")
            print(json.dumps({k: str(v) for k, v in result_state.items() if k != "messages"}, indent=2))
            
            return {"orchestrator_plan": serialized_plan}
            
        except Exception as e:
            print(f"\n⚠️  Orchestrator failed: {str(e)[:100]}")
            # Fallback: Return empty plan or handle error
            # Since next_module is required, we might want to default to something or raise. 
            # For now, let's re-raise to see the error during dev.
            raise e
