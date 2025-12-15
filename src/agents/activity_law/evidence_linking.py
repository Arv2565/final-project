from typing import Dict, Any, List
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.models.activity_law import EvidenceLinkingOutput
from src.prompts.activity_law_prompts import EVIDENCE_LINKING_PROMPT
from src.models import GraphState

class EvidenceLinkingAgent:
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=EvidenceLinkingOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("🔗 EVIDENCE LINKING AGENT")
        print("="*80)
        
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state or not activity_law_state.risk_assessment:
            print("⚠️  EvidenceLinkingAgent skipped: Missing risk assessment output")
            return {"evidence_linking": None}

        factors = activity_law_state.fact_structuring.factors
        events = activity_law_state.fact_structuring.events
        risk_matrix = activity_law_state.risk_assessment.risk_matrix
        
        print(f"\n📥 Input State:")
        print(f"   Risk Matrix: Available from risk assessment")
        print(f"   Factors: {len(factors) if factors else 0}")
        print(f"   Events: {len(events) if events else 0}")

        try:
            result = self.llm.invoke(
                EVIDENCE_LINKING_PROMPT.format(
                    risk_matrix=risk_matrix,
                    factors=factors,
                    events=events
                ),
                config={"callbacks": callbacks}
            )
            
            print(f"\n✅ Evidence Linking Output:")
            if result and hasattr(result, 'linked_evidence'):
                print(f"   Linked Evidence: {len(result.linked_evidence) if result.linked_evidence else 0} connections made")
            print(f"\n📤 Return: evidence_linking")
            
            return {"evidence_linking": result}
        except Exception as e:
            print(f"\n⚠️  EvidenceLinkingAgent failed: {str(e)[:100]}")
            return {"evidence_linking": None}
