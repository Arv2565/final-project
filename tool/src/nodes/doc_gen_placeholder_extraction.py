from typing import Dict, Any
from src.models import GraphState
from src.models.document_generation import TemplateInfo
from src.agents.document_generation.placeholder_extraction_agent import PlaceholderExtractionAgent

# Initialize agent
placeholder_extraction_agent = PlaceholderExtractionAgent()

def doc_gen_placeholder_extraction_node(state: GraphState) -> Dict[str, Any]:
    """
    Step 2: Extract placeholders from the selected template.
    """
    print("---DOC GEN: PLACEHOLDER EXTRACTION---")
    
    doc_state = state.get("document_generation_state", {})
    template_info: TemplateInfo = doc_state.get("selected_template")
    
    if not template_info:
        raise ValueError("No template selected")
         
    print(f"Extracting placeholders from {template_info.template_file}...")
    placeholders = placeholder_extraction_agent(template_info.template_file)
    
    new_doc_state = {
        **doc_state,
        "placeholders": placeholders,
        "status": "checking_input" 
    }
    
    return {"document_generation_state": new_doc_state}
