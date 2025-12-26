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
        """Classify, extract entities, and generate an execution plan.
        
        Args:
            state: GraphState containing 'router_output'
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'orchestrator_plan' field containing intent, entities, and steps
        """
        print("\n" + "="*80)
        print("🎯 ORCHESTRATOR AGENT (Merged)")
        print("="*80)
        
        router_output = state.get("router_output")
        
        if not router_output:
            raise ValueError("GraphState missing 'router_output' for OrchestratorAgent")

        cleaned_query = router_output.cleaned_query
        metadata = router_output.metadata

        print(f"\n📥 Input State:")
        import json
        print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))

        # Build user prompt
        user_prompt = f"Query: {cleaned_query}\n\n"
        if metadata.language and metadata.language != "en":
            user_prompt += f"(Originally in: {metadata.language})\n"
        
        user_prompt += """
        1. Classify the intent.
        2. Extract relevant entities.
        3. Create a plan to answer this query using only agent numbers 1-6.
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
            print(f"   Intent: {plan.intent}")
            print(f"   Entities: {plan.entities}")
            print(f"   Planning Steps:")
            for step in plan.steps:
                print(f"      - Agent {step.agent_number}: {step.reasoning[:80]}...")
            
            # Serialize for graph state
            serialized_plan = plan.model_dump()
            
            # We also populate 'classifier_output' for backward compatibility if other nodes rely on it,
            # BUT based on the plan we are removing the classifier node, so we might just put everything in orchestrator_plan.
            # However, for safety, let's also construct valid classifier_output structure if needed, 
            # but per plan, we are simplifying. Let's stick to orchestrator_plan carrying everything.
            
            result_state = {**state, "orchestrator_plan": serialized_plan}
            
            # Update 'classifier_output' in state just in case other nodes need it directly (e.g. downstream agents reading intent)
            # It's safer to keep the state consistent with what IntentClassifierAgent WOULD have produced.
            from src.models import IntentClassifierOutput
            classifier_output = IntentClassifierOutput(
                intent=plan.intent,
                entities=plan.entities
            )
            result_state["classifier_output"] = classifier_output
            
            print(f"\n📤 Full Graph State Update:")
            print(json.dumps({k: str(v) for k, v in result_state.items()}, indent=2))
            
            return {"orchestrator_plan": serialized_plan, "classifier_output": classifier_output}
            
        except Exception as e:
            print(f"\n⚠️  Orchestrator failed: {str(e)[:100]}")
            # Fallback: Return empty plan
            return {"orchestrator_plan": [], "classifier_output": None}
