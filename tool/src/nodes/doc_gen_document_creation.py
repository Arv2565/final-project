from typing import Dict, Any
from src.models import GraphState
from src.agents.document_generation.document_generation_agent import DocumentGenerationAgent

# Initialize agent
document_generation_agent_instance = DocumentGenerationAgent()

def doc_gen_document_creation_node(state: GraphState) -> Dict[str, Any]:
    """
    Step 4a: Generate the filled document using the DocumentGenerationAgent.
    """
    print("---DOC GEN: DOCUMENT CREATION---")
    
    doc_state = state.get("document_generation_state", {})
    template_info = doc_state.get("selected_template")
    placeholders = doc_state.get("placeholders", [])
    user_response = doc_state.get("user_inputs", "")
    
    print("Generating document content...")
    
    # Ensure placeholders is a list of dicts for the agent
    placeholders_list = []
    for p in placeholders:
        if hasattr(p, "dict"):
            placeholders_list.append(p.dict())
        else:
            placeholders_list.append(p)
            
    generated_doc = document_generation_agent_instance.generate(
        template_info.template_file,
        placeholders_list,
        user_response
    )
    
    new_doc_state = {
        **doc_state,
        "generated_document": generated_doc,
        "status": "generating_procedure" 
    }
    
    # We update the state. The next node will pick this up.
    return {
        "document_generation_state": new_doc_state,
        "generated_document_content": generated_doc 
    }
