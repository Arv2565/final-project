from typing import Dict, Any, List
from src.models import GraphState, ProceduralGuidanceState
from src.models.procedural_guidance import ActorMappingOutput
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.procedural_prompts import RESPONSIBLE_ACTOR_MAPPER_SYSTEM_PROMPT


class ResponsibleActorMapperAgent:
    """Maps which parties or officers are responsible for each procedural step."""
    
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=ActorMappingOutput,
        )
    
    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Map responsible actors to procedural steps.
        
        Args:
            state: GraphState containing router_output and procedural_guidance_state
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'actor_mapping' field
        """
        print("\n👥 RESPONSIBLE ACTOR MAPPER AGENT")
        print("=" * 60)
        
        router_output = state.get("router_output")
        if not router_output:
            raise ValueError("Missing 'router_output' in state")
        
        cleaned_query = router_output.cleaned_query
        
        # Get previous step outputs
        procedural_state = state.get("procedural_guidance_state", ProceduralGuidanceState())
        
        context_info = ""
        if procedural_state.checklist and procedural_state.checklist.items:
            context_info = "\n\nChecklist Items Generated:\n"
            for item in procedural_state.checklist.items[:5]:  # Show first 5
                context_info += f"- {item.description}\n"
        
        # Build user prompt
        user_prompt = f"""Query: {cleaned_query}
{context_info}

Map which parties and officers are responsible for each procedural step.

Consider:
- Who initiates this procedure? (Complainant, Accused, State)
- Which officers are involved? (Police, Magistrate, Prosecutor)
- What are their jurisdictions under BNSS?
- Where should people go? (Police station, court, etc.)

Be specific about roles and jurisdictions."""
        
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": RESPONSIBLE_ACTOR_MAPPER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"✅ Mapped {len(output.actor_mappings)} actor responsibilities")
            for mapping in output.actor_mappings[:3]:  # Show first 3
                print(f"   - {mapping.step}: {mapping.responsible_party}")
            
            return {"actor_mapping": output}
            
        except Exception as e:
            print(f"⚠️  Actor mapping failed: {str(e)[:100]}")
            raise
