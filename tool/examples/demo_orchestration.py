import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import (
    GraphState, 
    QueryRouterOutput, 
    QueryMetadata, 
    IntentClassifierOutput, 
    IntentType, 
    ExtractedEntities
)
from src.agents import (
    OrchestratorAgent,
    ActivityToLawAgent,
    ProceduralGuidanceAgent,
    DraftBuilderAgent,
    EducationalLayerAgent,
    CaseRetrieverAgent,
    ComparativeModuleAgent
)
from src.models.orchestrator import AgentType

def main():
    # Map agent types to instances
    agent_map = {
        AgentType.ACTIVITY_TO_LAW: ActivityToLawAgent(),
        AgentType.PROCEDURAL_GUIDANCE: ProceduralGuidanceAgent(),
        AgentType.DRAFT_BUILDER: DraftBuilderAgent(),
        AgentType.EDUCATIONAL_LAYER: EducationalLayerAgent(),
        AgentType.CASE_RETRIEVER: CaseRetrieverAgent(),
        AgentType.COMPARATIVE_MODULE: ComparativeModuleAgent(),
    }
    # Mock LLM for Orchestrator if API key is missing
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found. Using Mock LLM.")
        from unittest.mock import MagicMock, patch
        from src.models import OrchestratorPlan, NextStep
        
        mock_plan = OrchestratorPlan(
            steps=[
                NextStep(agent_id=AgentType.ACTIVITY_TO_LAW, reasoning="Map noise pollution to laws."),
                NextStep(agent_id=AgentType.PROCEDURAL_GUIDANCE, reasoning="Explain how to file a complaint."),
            ],
            final_response_needed=True
        )
        
        # Patch ChatOpenAI to avoid init error
        with patch('src.agents.orchestrator_agent.ChatOpenAI') as MockChat:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value.invoke.return_value = mock_plan
            MockChat.return_value = mock_llm
            
            orchestrator = OrchestratorAgent()
            
            # Run Orchestrator logic inside the patch context or with the mocked instance
            # Since we already instantiated it with the mock, we can proceed.
    else:
        orchestrator = OrchestratorAgent()



    # Mock Input Data
    print("\n--- Mocking Input Data ---")
    query = "I want to file a case against my neighbor for loud noise. How do I do that?"
    print(f"User Query: {query}")
    
    router_output = QueryRouterOutput(
        cleaned_query=query,
        metadata=QueryMetadata(original_language="en", language="en", has_personal_data=False, is_legal_question=True)
    )
    
    classifier_output = IntentClassifierOutput(
        intent=IntentType.ASK_PROCEDURE,
        entities=ExtractedEntities(jurisdiction="India", topic="Noise Pollution", time_frame="current")
    )
    
    state = GraphState(
        user_query=query,
        router_output=router_output,
        classifier_output=classifier_output
    )

    # Run Orchestrator
    print("\n--- Running Orchestrator ---")
    result = orchestrator(state)
    plan_steps = result.get("orchestrator_plan", [])
    
    print(f"Orchestrator Plan ({len(plan_steps)} steps):")
    for i, step in enumerate(plan_steps):
        print(f"{i+1}. Agent: {step['agent_id']}")
        print(f"   Reasoning: {step['reasoning']}")

    # Execute Plan
    print("\n--- Executing Plan ---")
    current_state = state.copy()
    
    for step in plan_steps:
        agent_id = step['agent_id']
        agent = agent_map.get(agent_id)
        
        if agent:
            print(f"Running {agent_id}...")
            output = agent(current_state)
            current_state.update(output)
            print(f"Output keys: {list(output.keys())}")
        else:
            print(f"Warning: No agent found for {agent_id}")

    print("\n--- Final State Summary ---")
    for key, value in current_state.items():
        if key not in ["user_query", "router_output", "classifier_output", "orchestrator_plan"]:
            print(f"{key}: {value}")

if __name__ == "__main__":
    main()
