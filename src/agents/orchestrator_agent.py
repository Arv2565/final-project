from typing import Dict, Any, List

from langchain_openai import ChatOpenAI

from src.models import GraphState, OrchestratorPlan
from src.config import get_llm_config
from src.prompts.orchestrator_agent import ORCHESTRATOR_SYSTEM_PROMPT


class OrchestratorAgent:
    """Central Brain that routes queries to specialized agents.
    
    Decides which agents to call based on intent and entities.
    """

    def __init__(self) -> None:
        config = get_llm_config()
        self.llm = ChatOpenAI(
            model=config.writer_model, # Using writer model for better reasoning
            temperature=config.temperature_writer,
        ).with_structured_output(OrchestratorPlan)

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Generate an execution plan.
        
        Args:
            state: GraphState containing 'router_output' and 'classifier_output'
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'orchestrator_plan' field containing list of steps
        """
        router_output = state.get("router_output")
        classifier_output = state.get("classifier_output")
        
        if not router_output or not classifier_output:
            raise ValueError("GraphState missing required outputs for OrchestratorAgent")

        cleaned_query = router_output.cleaned_query
        intent = classifier_output.intent
        entities = classifier_output.entities

        # Build user prompt
        user_prompt = f"""
        Query: {cleaned_query}
        Intent: {intent}
        Entities: {entities}
        
        Create a plan to answer this query.
        """

        try:
            plan = self.llm.invoke(
                [
                    {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            # Serialize steps for graph state
            serialized_steps = [step.model_dump() for step in plan.steps]
            
            return {"orchestrator_plan": serialized_steps}
            
        except Exception as e:
            # Fallback: If LLM fails, return empty plan or default
            print(f"Orchestrator failed: {e}")
            return {"orchestrator_plan": []}
