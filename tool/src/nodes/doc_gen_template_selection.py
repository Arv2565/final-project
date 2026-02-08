from typing import Dict, Any
from src.models import GraphState
from src.agents.document_generation.template_selection_agent import TemplateSelectionAgent

# Initialize agent
template_selection_agent = TemplateSelectionAgent()

def doc_gen_template_selection_node(state: GraphState) -> Dict[str, Any]:
    """
    Step 1: Select the appropriate document template based on user query.
    """
    print("---DOC GEN: TEMPLATE SELECTION---")
    
    # Initialize state if missing
    doc_state = state.get("document_generation_state", {})
    if not doc_state:
        doc_state = {
            "status": "selecting_template",
            "selected_template": None,
            "placeholders": [],
            "user_inputs": {},
            "generated_document": None,
            "generated_procedure": None
        }
    
    query = state.get("user_query")
    print("Selecting template...")
    selected_template = template_selection_agent(query)
    
    new_doc_state = {
        **doc_state,
        "status": "extracting_placeholders",
        "selected_template": selected_template
    }
    
    return {"document_generation_state": new_doc_state}
