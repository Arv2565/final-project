import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import GraphState
from src.models.query_router import QueryRouterOutput
from src.agents.activity_law.workflow import ActivityToLawWorkflow
import json

def test_activity_law_workflow():
    print("Initializing Workflow...")
    workflow = ActivityToLawWorkflow()

    # Mock State
    sample_query = "I was walking in the tech park yesterday evening around 6 PM, and a guy on a bike snatched my phone and drove away. I tried to chase him but he was too fast."
    
    state: GraphState = {
        "user_query": sample_query,
        "router_output": QueryRouterOutput(
            cleaned_query=sample_query,
            is_legal=True,
            confidence_score=0.9
        )
    }

    print(f"Running workflow for query: {sample_query}")
    result = workflow(state)
    
    activity_state = result.get("activity_law_state")
    if activity_state:
        print("\nWorkflow Execution Successful!")
        print("-" * 50)
        
        if activity_state.fact_structuring:
            print(f"Factors: {len(activity_state.fact_structuring.factors)}")
            print(f"Events: {len(activity_state.fact_structuring.events)}")
            
        if activity_state.statute_matching:
            print(f"Candidates: {len(activity_state.statute_matching.candidate_statutes)}")
            for m in activity_state.statute_matching.candidate_statutes:
                print(f" - {m.provision} (Score: {m.match_score})")

        if activity_state.rule_matching:
            print(f"Rule Assessments: {len(activity_state.rule_matching.rule_assessments)}")

        if activity_state.risk_assessment:
            print(f"Risks: {len(activity_state.risk_assessment.risk_matrix)}")
            
        if activity_state.evidence_linking:
            print(f"Evidence Links: {len(activity_state.evidence_linking.evidence_links)}")

        # Dump full JSON to file for inspection
        with open("workflow_output_dump.json", "w") as f:
            f.write(activity_state.model_dump_json(indent=2))
        print("\nFull output dumped to workflow_output_dump.json")
        
    else:
        print("Workflow failed to produce activity_law_state")

if __name__ == "__main__":
    test_activity_law_workflow()
