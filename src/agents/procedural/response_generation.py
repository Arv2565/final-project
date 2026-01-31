from typing import Dict, Any, List
from src.models import GraphState, ProceduralGuidanceState
from src.agents.agent_llm_helper import get_agent_llm
from pydantic import BaseModel, Field

<<<<<<< HEAD

=======
from src.prompts.procedural_civil_prompts import CIVIL_PROCEDURAL_RESPONSE_PROMPT
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
class ProceduralResponseOutput(BaseModel):
    """Final user-facing response for procedural guidance."""
    summary: str = Field(..., description="Executive summary of the procedural guidance")
    detailed_response: str = Field(..., description="Comprehensive, well-formatted response with all steps")


<<<<<<< HEAD
PROCEDURAL_RESPONSE_PROMPT = """You are a legal document generator. Your output will be converted to a formal PDF.

formatting instructions:
- Use Markdown for structure.
- use # for main titles (e.g. # What is Divorce?)
- use ## for section headers (e.g. ## Procedure for Divorce)
- use **bold** for emphasis on key terms.
- Use numbered lists (1., 2.) for steps.
- Use bullet points (- ) where appropriate.
- Do NOT use code blocks or markdown metadata.

STRUCTURE OF RESPONSE:
1. **What is <Topic>?**: Brief legal definition.
2. **Why is <Topic> required?**: Purpose and necessity.
3. **What should a <Topic> cover?**: Key components (use a list).
4. **Format for <Topic>**:
   - Provide a template structure.
   - CENTER the title: "DRAFT OF <DOCUMENT NAME>" (The PDF generator handles centering).
   - Use standard legal clauses (WHEREAS, NOW THIS AGREEMENT WITNESSETH).
5. **Documents Required**: Checklist of mandatory documents.
6. **Procedure**: Step-by-step procedural guide with timelines.
7. **Legal Considerations**: Relevant acts (BNSS, Evidence Act) and jurisdiction.
8. **How can a lawyer help?**: Value of legal counsel.

IMPORTANT:
- Be concise and direct.
- **CRITICAL**: If specific details (names, dates, amounts, locations, clauses) are missing, you **MUST** use this EXACT format: `[MISSING: Description]`.
  - CORRECT: `[MISSING: Name of Accused]`, `[MISSING: FIR Number]`, `[MISSING: Date of Arrest]`
  - INCORRECT: `[Name]`, `...`, `___`, `(Date)`
- Do not invent details. Leave them as `[MISSING: ...]` so the user can fill them in later.
"""
=======
PROCEDURAL_RESPONSE_PROMPT = """You are a legal assistant providing clear, actionable procedural guidance.

Your role is to synthesize all procedural information into a comprehensive, user-friendly response.

Format the response as follows:

## SUMMARY
[2-3 sentence overview of what the user needs to do]

## TIMELINE & DEADLINES
[List all critical deadlines and time constraints]

## DOCUMENTS REQUIRED
[Prioritized checklist of documents to prepare]
- HIGH PRIORITY: [Items that are legally mandatory or time-critical]
- MEDIUM PRIORITY: [Important items]
- LOW PRIORITY: [Optional but helpful items]

## WHO TO CONTACT
[List responsible parties and officers with contact information]

## STEP-BY-STEP PROCEDURE
[Numbered list of ordered steps with details for each]

For each step include:
- What to do
- Who is responsible
- Required documents
- Estimated time
- Estimated cost
- Where to go/whom to contact
- Legal reference

## TOTAL ESTIMATES
- Overall Timeline: [X to Y timeframe]
- Overall Cost: [₹X to ₹Y range]

## IMPORTANT NOTES
[Any critical warnings, tips, or considerations]

Make the response conversational but precise. Use bullet points and formatting for easy readability.
Reference BNSS sections where relevant for legal credibility."""
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e


class ProceduralResponseGenerationAgent:
    """Generates final user-facing response from procedural guidance state."""
    
    def __init__(self):
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=ProceduralResponseOutput,
        )
    
    def __call__(self, state: GraphState, callbacks: List[Any] = []) -> Dict[str, Any]:
        """Generate final response from procedural guidance state.
        
        Args:
            state: GraphState containing procedural_guidance_state
            callbacks: List of LangChain callbacks
            
        Returns:
            Dict with 'final_response' field
        """
        print("\n📝 PROCEDURAL RESPONSE GENERATION AGENT")
        print("=" * 60)
        
        router_output = state.get("router_output")
        procedural_state = state.get("procedural_guidance_state", ProceduralGuidanceState())
        
        if not router_output or not procedural_state:
            raise ValueError("Missing required state for response generation")
        
        cleaned_query = router_output.cleaned_query
        
        # Build context from all procedural guidance components
        context = f"User Query: {cleaned_query}\n\n"
        
        # Timeline Constraints
        if procedural_state.timeline_constraints and procedural_state.timeline_constraints.constraints:
            context += "TIMELINE CONSTRAINTS:\n"
            for c in procedural_state.timeline_constraints.constraints:
                context += f"- {c.constraint_type}: {c.description}\n"
                context += f"  Time Limit: {c.time_limit}\n"
                context += f"  Reference: {c.statutory_reference}\n"
                context += f"  Consequences: {c.consequences}\n\n"
        
        # Checklist
        if procedural_state.checklist and procedural_state.checklist.items:
            context += "DOCUMENTS & ITEMS TO PREPARE:\n"
            for item in procedural_state.checklist.items:
                context += f"- [{item.priority.upper()}] {item.description}\n"
                context += f"  Reason: {item.reason}\n"
                context += f"  Legal Basis: {item.statutory_basis}\n\n"
        
        # Actor Mapping
        if procedural_state.actor_mapping and procedural_state.actor_mapping.actor_mappings:
            context += "RESPONSIBLE ACTORS:\n"
            for mapping in procedural_state.actor_mapping.actor_mappings:
                context += f"- Step: {mapping.step}\n"
                context += f"  Party: {mapping.responsible_party}\n"
                if mapping.responsible_officer:
                    context += f"  Officer: {mapping.responsible_officer}\n"
                context += f"  Contact: {mapping.contact_info}\n"
                context += f"  Reference: {mapping.statutory_reference}\n\n"
        
        # Ordered Steps
        if procedural_state.estimated_effort:
            effort = procedural_state.estimated_effort
            context += f"OVERALL ESTIMATES:\n"
            context += f"- Total Time: {effort.total_estimated_time}\n"
            context += f"- Total Cost: {effort.total_estimated_cost}\n\n"
            
            context += "ORDERED PROCEDURAL STEPS:\n"
            for step in effort.ordered_steps:
                context += f"\nStep {step.step_number}: {step.action}\n"
                context += f"- Responsible: {', '.join(step.responsible_actors)}\n"
                context += f"- Time: {step.estimated_time}\n"
                context += f"- Cost: {step.estimated_cost}\n"
                if step.required_documents:
                    context += f"- Documents: {', '.join(step.required_documents)}\n"
                if step.forms:
                    context += f"- Forms: {', '.join(step.forms)}\n"
                if step.contact_points:
                    context += f"- Contact: {', '.join(step.contact_points)}\n"
                context += f"- Legal Ref: {step.statutory_reference}\n"
        
        # Build user prompt
        user_prompt = f"""{context}

Synthesize all the above information into a clear, comprehensive, user-friendly response.
Follow the structured format provided in the system prompt.
Make it actionable and easy to understand for someone navigating the legal system."""
        
<<<<<<< HEAD
        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": PROCEDURAL_RESPONSE_PROMPT},
=======
        active_domain = state.get("active_legal_domain", "criminal")
        system_prompt = CIVIL_PROCEDURAL_RESPONSE_PROMPT if active_domain == "civil" else PROCEDURAL_RESPONSE_PROMPT

        try:
            output = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
>>>>>>> 14a165ddc199668c3ad8563ab4d99d899b1c0e5e
                    {"role": "user", "content": user_prompt},
                ],
                config={"callbacks": callbacks}
            )
            
            print(f"✅ Generated final response")
            print(f"   Summary length: {len(output.summary)} chars")
            print(f"   Detailed response length: {len(output.detailed_response)} chars")
            
            # Return the detailed response as final_response
            return {"final_response": output.detailed_response}
            
        except Exception as e:
            print(f"⚠️  Response generation failed: {str(e)[:100]}")
            raise
