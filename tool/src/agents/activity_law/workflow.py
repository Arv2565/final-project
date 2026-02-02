from typing import Dict, Any, List, Optional
from src.config.observability import get_langfuse_callback
from src.models import GraphState
from src.models.activity_law import ActivityLawState
from src.agents.activity_law.fact_structuring import FactStructuringAgent
from src.agents.activity_law.statute_matching import StatuteMatchingAgent
from src.agents.activity_law.rule_matching import RuleMatchingAgent
from src.agents.activity_law.risk_assessment import RiskAssessmentAgent
from src.agents.activity_law.evidence_linking import EvidenceLinkingAgent

class ActivityToLawWorkflow:
    """Orchestrates the 5-step Activity to Law Mapping workflow."""

    def __init__(self):
        self.fact_structuring_agent = FactStructuringAgent()
        self.statute_matching_agent = StatuteMatchingAgent()
        self.rule_matching_agent = RuleMatchingAgent()
        self.risk_assessment_agent = RiskAssessmentAgent()
        self.evidence_linking_agent = EvidenceLinkingAgent()
        self.callback_handler = get_langfuse_callback()

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Execute the workflow sequence.
        
        Args:
            state: GraphState
            callbacks: List of LangChain callbacks (for trace propagation)
        """
        print(">>> STARTING ACTIVITY TO LAW WORKFLOW")
        
        # Use passed callbacks if available, otherwise fallback to internal handler
        # If internal handler exists, we can append it, but usually one is enough and we want the parent trace.
        active_callbacks = callbacks if callbacks else ([self.callback_handler] if self.callback_handler else [])

        # Initialize Accumulator State if not present, though usually we start fresh
        current_activity_state = state.get("activity_law_state", ActivityLawState())
        
        # 1. Fact Structuring
        fact_result = self.fact_structuring_agent(state, callbacks=active_callbacks)
        if fact_result and fact_result.get("fact_structuring"):
            current_activity_state.fact_structuring = fact_result["fact_structuring"]
        
        # Update state for next step
        state["activity_law_state"] = current_activity_state

        # 2. Statute Matching
        statute_result = self.statute_matching_agent(state, callbacks=active_callbacks)
        if statute_result and statute_result.get("statute_matching"):
            current_activity_state.statute_matching = statute_result["statute_matching"]
        
        state["activity_law_state"] = current_activity_state

        # 3. Rule Matching
        rule_result = self.rule_matching_agent(state, callbacks=active_callbacks)
        if rule_result and rule_result.get("rule_matching"):
            current_activity_state.rule_matching = rule_result["rule_matching"]
        
        state["activity_law_state"] = current_activity_state

        # 4. Risk Assessment
        risk_result = self.risk_assessment_agent(state, callbacks=active_callbacks)
        if risk_result and risk_result.get("risk_assessment"):
            current_activity_state.risk_assessment = risk_result["risk_assessment"]
        
        state["activity_law_state"] = current_activity_state

        # 5. Evidence Linking
        evidence_result = self.evidence_linking_agent(state, callbacks=active_callbacks)
        if evidence_result and evidence_result.get("evidence_linking"):
            current_activity_state.evidence_linking = evidence_result["evidence_linking"]
        
        state["activity_law_state"] = current_activity_state
        
        # Determine final easy-access list of laws for backward compatibility if needed
        legal_laws = []
        if current_activity_state.statute_matching:
            legal_laws = [m.provision for m in current_activity_state.statute_matching.candidate_statutes]

        print("<<< ACTIVITY TO LAW WORKFLOW COMPLETED")
        
        return {
            "activity_law_state": current_activity_state,
            "legal_laws": legal_laws # Populate legacy field
        }
