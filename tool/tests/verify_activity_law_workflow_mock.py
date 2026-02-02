import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import GraphState
from src.models.query_router import QueryRouterOutput
from src.agents.activity_law.workflow import ActivityToLawWorkflow
from src.models.activity_law import (
    FactStructuringOutput, FactFactor, Event,
    StatuteMatchingOutput, StatuteMatch,
    RuleMatchingOutput, RuleMatch,
    RiskAssessmentOutput, RiskAssessment,
    EvidenceLinkingOutput, ProvisionEvidence, EvidenceLink
)

def mock_llm_invoke(prompt, *args, **kwargs):
    """Return specific structured outputs based on which agent is calling."""
    # We can detect agent by checking prompt content or specific mock setup
    # But simpler: we will patch the agents in the workflow
    return None # Base handler

def test_activity_law_workflow_mock():
    print("Initializing Workflow with Mocks...")
    
    # Mocking at the class level where ChatOpenAI is instantiated would be complex
    # So we instantiate the workflow, then replace agents' llm attributes with mocks
    
    with patch('src.agents.activity_law.fact_structuring.ChatOpenAI') as MockLlm1, \
         patch('src.agents.activity_law.statute_matching.ChatOpenAI') as MockLlm2, \
         patch('src.agents.activity_law.rule_matching.ChatOpenAI') as MockLlm3, \
         patch('src.agents.activity_law.risk_assessment.ChatOpenAI') as MockLlm4, \
         patch('src.agents.activity_law.evidence_linking.ChatOpenAI') as MockLlm5:
         
        # Setup Mocks to return 'with_structured_output' which returns an invokable
        
        # 1. Fact Structuring Mock
        mock_fs_llm = MagicMock()
        mock_fs_llm.invoke.return_value = FactStructuringOutput(
            factors=[FactFactor(factor_id="F1", type="person", value="User")],
            events=[Event(event_id="E1", action="theft", description="Phone snatched", actors=["User", "Thief"])]
        )
        MockLlm1.return_value.with_structured_output.return_value = mock_fs_llm

        # 2. Statute Matching Mock
        mock_sm_llm = MagicMock()
        mock_sm_llm.invoke.return_value = StatuteMatchingOutput(
            candidate_statutes=[StatuteMatch(provision="IPC 378", match_score=0.9, reasoning="Theft")]
        )
        MockLlm2.return_value.with_structured_output.return_value = mock_sm_llm

        # 3. Rule Matching Mock
        mock_rm_llm = MagicMock()
        mock_rm_llm.invoke.return_value = RuleMatchingOutput(
            rule_assessments=[RuleMatch(provision="IPC 378", applicability="uncertain", notes="Need to prove intent")]
        )
        MockLlm3.return_value.with_structured_output.return_value = mock_rm_llm

        # 4. Risk Assessment Mock
        mock_ra_llm = MagicMock()
        mock_ra_llm.invoke.return_value = RiskAssessmentOutput(
            risk_matrix=[RiskAssessment(provision="IPC 378", likelihood_of_applicability=0.5, potential_penalty="3 years", recommended_action="File FIR")]
        )
        MockLlm4.return_value.with_structured_output.return_value = mock_ra_llm

        # 5. Evidence Linking Mock
        mock_el_llm = MagicMock()
        mock_el_llm.invoke.return_value = EvidenceLinkingOutput(
            evidence_links=[ProvisionEvidence(provision="IPC 378", element_mappings=[], explanation="Possible theft")]
        )
        MockLlm5.return_value.with_structured_output.return_value = mock_el_llm

        # Instantiation
        workflow = ActivityToLawWorkflow()

    # Mock State
    sample_query = "I was walking... and phone snatched."
    state: GraphState = {
        "user_query": sample_query,
        "router_output": QueryRouterOutput(
            cleaned_query=sample_query,
            metadata={"is_legal_question": True}
        )
    }

    print(f"Running MOCKED workflow for query: {sample_query}")
    result = workflow(state)
    
    activity_state = result.get("activity_law_state")
    
    if activity_state and activity_state.fact_structuring:
        print("\nWorkflow Execution Successful (MOCKED)!")
        print(f"Factors Extracted: {len(activity_state.fact_structuring.factors)}")
        print(f"Statute Candidates: {len(activity_state.statute_matching.candidate_statutes)}")
        print(f"Applicability: {activity_state.rule_matching.rule_assessments[0].applicability}")
    else:
        print("Workflow failed to produce state.")
        exit(1)

if __name__ == "__main__":
    test_activity_law_workflow_mock()
