import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

# Load env vars
load_dotenv(Path(__file__).parent.parent / ".env")

from src.models import GraphState, QueryRouterOutput, QueryMetadata
from src.agents.orchestrator_agent import OrchestratorAgent

def verify_merged_agent():
    print("🚀 Verifying Merged Orchestrator Agent...")
    
    agent = OrchestratorAgent()
    
    # Mock input state
    state = {
        "router_output": QueryRouterOutput(
            cleaned_query="How do I file for divorce in India?",
            metadata=QueryMetadata(
                original_language="en",
                detected_language="en",
                confidence=1.0,
                translated_query="How do I file for divorce in India?"
            )
        )
    }
    
    print(f"\n📝 Input Query: {state['router_output'].cleaned_query}")
    
    try:
        result = agent(state)
        plan = result.get("orchestrator_plan")
        classifier_output = result.get("classifier_output")
        
        print("\n✅ Result:")
        print(f"   Intent: {plan['intent']}")
        print(f"   Entities: {plan['entities']}")
        print(f"   Steps: {len(plan['steps'])}")
        
        if classifier_output:
            print(f"\n✅ Classifier Output (Backward Compat):")
            print(f"   Intent: {classifier_output.intent}")
        
        # Verify structure
        assert plan['intent'] is not None
        assert plan['entities'] is not None
        assert len(plan['steps']) > 0
        
        print("\n🎉 Verification Successful!")
        
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_merged_agent()
