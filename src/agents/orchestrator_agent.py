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

        print(f"\n📥 Input State:")
        import json
        # Safe printing of state (excluding large objects if any)
        print(json.dumps({k: str(v) for k, v in state.items() if k != "messages"}, indent=2))

        # Build user prompt
        user_prompt = f"Query: {cleaned_query}\n\n"
        if metadata.language and metadata.language != "en":
            user_prompt += f"(Originally in: {metadata.language})\n"
        
        user_prompt += """
        Determine the single best next module (agent number 1-6) to handle this query.
        """

        try:
            plan = self.llm.invoke(
                [
                    {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Orchestrator Output:")
            print(f"   Selected Module: {plan.next_module.agent_number}")
            print(f"   Reasoning: {plan.next_module.reasoning}")
            
            # Serialize for graph state
            serialized_plan = plan.model_dump()
            
            result_state = {**state, "orchestrator_plan": serialized_plan}
            
            print(f"\n📤 Full Graph State Update:")
            print(json.dumps({k: str(v) for k, v in result_state.items() if k != "messages"}, indent=2))
            
            return {"orchestrator_plan": serialized_plan}
            
        except Exception as e:
            print(f"\n⚠️  Orchestrator failed: {str(e)[:100]}")
            # If the LLM returned a raw integer or something that failed parsing, we might be able to recover
            # But since we're using structued output, debugging the prompt is better.
            # However, let's at least try to be helpful if it's a known pattern.
            
            import re
            # Check if the error message mentions "Input should be a valid dictionary... input_value=1"
            # This happens if the model just returned "1"
            
            match = re.search(r"input_value=(\d+)", str(e))
            if match:
                agent_num = int(match.group(1))
                print(f"⚠️  Recovering from raw integer output: {agent_num}")
                
                from src.models import OrchestratorPlan, NextModule
                
                # Construct a fallback plan
                fallback_plan = OrchestratorPlan(
                    next_module=NextModule(
                        agent_number=agent_num,
                        reasoning="Fallback recovery from raw integer output."
                    )
                )
                serialized_plan = fallback_plan.model_dump()
                return {"orchestrator_plan": serialized_plan}

            raise e
