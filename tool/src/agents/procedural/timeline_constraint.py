from typing import Dict, Any, List
from src.models import GraphState
from src.models.procedural_guidance import TimelineConstraintOutput
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.procedural_prompts import TIMELINE_CONSTRAINT_SYSTEM_PROMPT
from src.prompts.procedural_civil_prompts import CIVIL_TIMELINE_CONSTRAINT_SYSTEM_PROMPT


class TimelineConstraintAgent:
    """Identifies deadlines, limitation periods, and filing windows based on BNSS."""
    
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=TimelineConstraintOutput,
        )
    
    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Identify timeline constraints from user query.
        
        Args:
            state: GraphState containing router_output
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'timeline_constraints' field
        """
        print("\n🕐 TIMELINE/CONSTRAINT IDENTIFIER AGENT")
        print("=" * 60)
        
        router_output = state.get("router_output")
        active_domain = state.get("active_legal_domain", "criminal") # Default to criminal if not set
        
        if not router_output:
            raise ValueError("Missing 'router_output' in state")
        
        cleaned_query = router_output.cleaned_query
        metadata = router_output.metadata if router_output else None

        language_map = {
            "en": "English",
            "hi": "Hindi",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
            "ja": "Japanese",
            "zh": "Chinese",
            "ta": "Tamil",
            "te": "Telugu",
            "kn": "Kannada",
            "ml": "Malayalam",
        }
        original_language_code = (metadata.original_language or metadata.language or "en") if metadata else "en"
        response_language_name = language_map.get(original_language_code, "English")
        
        # Clarification Logic
        clarification_counts = state.get("clarification_counts", {})
        current_count = clarification_counts.get("procedural_guidance", 0)
        MAX_CLARIFICATION = 3
        
        clarification_history = state.get("clarification_history", [])
        
        # Build user prompt
        user_prompt = f"""Query: {cleaned_query}

Identify all relevant timeline constraints, deadlines, limitation periods, and filing windows for this procedural matter.

Consider:
- What type of procedural step is this? (FIR, bail, trial, appeal, etc.)
- What are the statutory deadlines under BNSS?
- What are the consequences of missing these deadlines?

Be precise with BNSS section references."""

        if clarification_history:
             user_prompt += "\n\n### ADDITIONAL CONTEXT FROM CLARIFICATIONS (CRITICAL - DO NOT IGNORE):\n"
             for item in clarification_history:
                 user_prompt += f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}\n"
             user_prompt += "\n\n‼️ CRITICAL INSTRUCTION: The user has ALREADY provided answers to the above questions. You MUST incorporate this information into your analysis. DO NOT REQUEST CLARIFICATION FOR ANY INFORMATION THAT HAS ALREADY BEEN PROVIDED ABOVE. If the user answered 'Muslim', you have all the information you need about personal law. Proceed with your analysis based on Muslim Personal Law."

        if current_count < MAX_CLARIFICATION:
             user_prompt += """

If the query is missing critical procedural context (e.g., Jurisdiction, Relief Sought, Religion for personal law, or specific relevant dates), you MAY request clarification. 

CRITICAL INSTRUCTION FOR CLARIFICATION:
- You are speaking to a layman who does not know legal terms.
- Do NOT ask "Which personal law applies?".
- INSTEAD ask simple questions like: "Are you Hindu, Muslim, Christian, or married under a Special Marriage Act?" or "Where did the incident happen?"
- Keep the question SIMPLE, DIRECT, and human-like.
- Set 'clarification' field and leave 'constraints' empty."""
             user_prompt += (
                 f"\n- IMPORTANT: The clarification question and reason MUST be in {response_language_name} "
                 f"(language code: {original_language_code})."
             )
        else:
             user_prompt += "\n\nYou have reached the limit for clarifications. You MUST make best-guess assumptions based on general Indian criminal procedure."
        
        system_prompt = CIVIL_TIMELINE_CONSTRAINT_SYSTEM_PROMPT if active_domain == "civil" else TIMELINE_CONSTRAINT_SYSTEM_PROMPT
        
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"✅ Timeline Agent Output Check")
            
            if output.clarification:
                print(f"   Requesting Clarification: {output.clarification.question}")
                return {
                    "timeline_constraints": output,
                    "needs_clarification": True,
                    "ambiguity_remover_scope": "procedural",
                    "ambiguity_remover_context": {
                        "agent": "procedural_guidance",
                        "legal_domain": active_domain,
                        "constraints_extracted": len(output.constraints or []),
                        "agent_requested_question": output.clarification.question,
                        "agent_requested_reason": output.clarification.reason,
                    },
                    "current_agent": "procedural_guidance",
                    "ambiguity_remover_next": "checklist_generator",
                } # Node must handle the merge
            
            print(f"✅ Identified {len(output.constraints)} timeline constraints")
            for constraint in output.constraints:
                print(f"   - {constraint.constraint_type}: {constraint.description}")
            
            return {"timeline_constraints": output}
            
        except Exception as e:
            print(f"⚠️  Timeline constraint identification failed: {str(e)[:100]}")
            raise
