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
        """Generate an execution plan with numeric agent IDs.
        
        Args:
            state: GraphState containing 'router_output' and 'classifier_output'
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'orchestrator_plan' field containing list of steps with numeric agent_number
        """
        print("\n" + "="*80)
        print("🎯 ORCHESTRATOR AGENT")
        print("="*80)
        
        router_output = state.get("router_output")
        classifier_output = state.get("classifier_output")
        
        if not router_output or not classifier_output:
            raise ValueError("GraphState missing required outputs for OrchestratorAgent")

        cleaned_query = router_output.cleaned_query
        intent = classifier_output.intent
        entities = classifier_output.entities

        print(f"\n📥 Input State:")
        import json
        print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))

        # Build user prompt
        user_prompt = f"""
        Query: {cleaned_query}
        Intent: {intent}
        Entities: {entities}
        
        Create a plan to answer this query using only agent numbers 1-6.
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
            print(f"   Planning Steps:")
            for step in plan.steps:
                print(f"      - Agent {step.agent_number}: {step.reasoning[:80]}...")
            
            # Serialize steps for graph state (now with agent_number instead of agent_id)
            serialized_steps = [step.model_dump() for step in plan.steps]
            
            result_state = {**state, "orchestrator_plan": serialized_steps}
            print(f"\n📤 Full Graph State Update:")
            print(json.dumps({k: str(v) for k, v in result_state.items()}, indent=2))
            
            # Serialize steps for graph state (now with agent_number instead of agent_id)
            serialized_steps = [step.model_dump() for step in plan.steps]
            
            return {"orchestrator_plan": serialized_steps}
            
        except Exception as e:
            print(f"\n⚠️  Orchestrator failed: {str(e)[:100]}")
            # Fallback: If LLM fails, return empty plan or default
            return {"orchestrator_plan": []}
