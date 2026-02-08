from typing import Dict, Any
from src.models import GraphState
from src.agents.document_generation.procedure_generation_agent import ProcedureGenerationAgent

# Initialize agent
procedure_generation_agent = ProcedureGenerationAgent()

def doc_gen_procedure_generation_node(state: GraphState) -> Dict[str, Any]:
    """
    Step 4b: Generate the procedural guidance (steps) related to the document.
    """
    print("---DOC GEN: PROCEDURE GENERATION---")
    
    doc_state = state.get("document_generation_state", {})
    template_info = doc_state.get("selected_template")
    
    # We expect document creation to have run, but procedure generation is independent mostly
    # It just needs template info.
    
    print("Generating procedural steps...")
    
    generated_proc = procedure_generation_agent(
        template_info.procedure_file,
        template_info.name
    )
    
    new_doc_state = {
        **doc_state,
        "generated_procedure": generated_proc,
        "status": "completed"
    }
    
    return {
        "document_generation_state": new_doc_state,
        "final_response": f"I have generated the {template_info.name} for you.",
        # generated_document_content is already set by previous node, or could be re-set here if needed
        # but the state merging will handle it if we don't overwrite it with None.
    }
