from typing import Dict, Any
from src.models import GraphState
from src.agents.document_generation.procedure_generation_agent import ProcedureGenerationAgent

# Language code to full name mapping
LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
}

# Initialize agent
procedure_generation_agent = ProcedureGenerationAgent()

def doc_gen_procedure_generation_node(state: GraphState) -> Dict[str, Any]:
    """
    Step 4b: Generate the procedural guidance (steps) related to the document.
    The procedure is generated in the user's original language if available.
    """
    print("---DOC GEN: PROCEDURE GENERATION---")
    
    doc_state = state.get("document_generation_state", {})
    template_info = doc_state.get("selected_template")
    
    # Extract original language from router output
    router_output = state.get("router_output")
    original_language_code = "en"  # Default
    if router_output and hasattr(router_output, 'metadata') and router_output.metadata:
        original_language_code = router_output.metadata.original_language or "en"
    
    response_language_name = LANGUAGE_MAP.get(original_language_code, "English")
    print(f"Generating procedural steps in {response_language_name} (code: {original_language_code})...")
    
    # We expect document creation to have run, but procedure generation is independent mostly
    # It just needs template info.
    
    print("Generating procedural steps...")
    
    generated_proc = procedure_generation_agent(
        template_info.procedure_file,
        template_info.name,
        language_code=original_language_code
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
