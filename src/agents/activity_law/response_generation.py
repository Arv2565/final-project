from typing import Dict, Any, List
from pydantic import BaseModel, Field
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.activity_law_prompts import RESPONSE_GENERATION_PROMPT
from src.models import GraphState

class ResponseGenerationOutput(BaseModel):
    """Output schema for the final response generation."""
    final_response: str = Field(description="The comprehensive final answer to the user query.")

class ResponseGenerationAgent:
    def __init__(self):
        # We use 'writer' model type for generating long-form text
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=ResponseGenerationOutput,
        )

    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("📝 RESPONSE GENERATION AGENT")
        print("="*80)
        
        # Log full input state
        import json
        print(f"\n📥 Input State:")
        print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))

        # Extract context variables
        router_output = state.get("router_output")
        query = router_output.cleaned_query if router_output else state.get("user_query", "")
        language = router_output.metadata.language if router_output and router_output.metadata else "English"
        
        activity_law_state = state.get("activity_law_state")
        if not activity_law_state:
            print("⚠️  ResponseGenerationAgent skipped: Missing activity_law_state")
            return {"final_response": "I apologize, but I couldn't complete the legal analysis due to missing internal data."}

        # Safely extract components, handling potential None values
        fact_structuring = activity_law_state.fact_structuring
        factors = fact_structuring.factors if fact_structuring else []
        events = fact_structuring.events if fact_structuring else []
        
        statute_matching = activity_law_state.statute_matching
        statutes = statute_matching.candidate_statutes if statute_matching else []
        
        rule_matching = activity_law_state.rule_matching
        rules = rule_matching.rule_assessments if rule_matching else []
        
        risk_assessment = activity_law_state.risk_assessment
        risks = risk_assessment.risk_matrix if risk_assessment else []
        
        evidence_linking = activity_law_state.evidence_linking
        evidence = evidence_linking.evidence_links if evidence_linking else []

        try:
            result = self.llm.invoke(
                RESPONSE_GENERATION_PROMPT.format(
                    query=query,
                    language=language,
                    factors=factors,
                    events=events,
                    statutes=statutes,
                    rules=rules,
                    risks=risks,
                    evidence=evidence
                ),
                config={"callbacks": callbacks}
            )
            
            final_response = result.final_response
            
            print(f"\n✅ Response Generated:")
            print(f"{final_response[:200]}...")
            
            # Construct result state for logging
            result_state = {**state, "final_response": final_response}
            print(f"\n📤 Full Graph State Update:")
            print(json.dumps({k: str(v) for k, v in result_state.items()}, indent=2))
            
            return {"final_response": result.final_response}
            
        except Exception as e:
            print(f"\n⚠️  ResponseGenerationAgent failed: {str(e)[:100]}")
            return {"final_response": f"Error generating response: {str(e)}"}
