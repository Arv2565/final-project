import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Manually load .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"').strip("'")

from src.agents.orchestrator_agent import OrchestratorAgent
from src.models import GraphState, QueryRouterOutput, QueryMetadata

def test_orchestrator():
    agent = OrchestratorAgent()
    
    # Mock state
    router_output = QueryRouterOutput(
        cleaned_query="I want to draft a rental agreement for my shop.",
        metadata=QueryMetadata(
            original_language="en",
            language="en",
            has_personal_data=False,
            is_legal_question=True
        )
    )
    
    state = GraphState(
        messages=[],
        router_output=router_output
    )
    
    print("Invoking Orchestrator Agent...")
    result = agent(state)
    
    plan = result.get("orchestrator_plan")
    
    print("\nResult Plan:")
    print(plan)
    
    if not plan:
        print("❌ FAILED: No plan returned")
        return

    # Check for next_module
    if 'next_module' in plan:
        nm = plan['next_module']
        print(f"\n✅ SUCCESS: Selected Module {nm['agent_number']}")
        print(f"Reasoning: {nm['reasoning']}")
        
        # Verify it's draft_builder (Agent 3) for this query
        if nm['agent_number'] == 3:
            print("✅ Logic Correct: Selected Draft Builder")
        else:
            print(f"⚠️  Logic Warning: Expected 3, got {nm['agent_number']}")
    else:
        print("❌ FAILED: 'next_module' not found in plan")

if __name__ == "__main__":
    test_orchestrator()
