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
    
    # The procedure text is the main response to the user.
    # The LLM now generates properly formatted markdown with all required sections.
    final_response_text = generated_proc

    # Preserve top-level generated_document_content if it exists so the WebSocket handler can send it.
    result = {
        "document_generation_state": new_doc_state,
        "final_response": final_response_text,
    }

    if state.get("generated_document_content"):
        result["generated_document_content"] = state.get("generated_document_content")

    return result
