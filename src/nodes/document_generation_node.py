from typing import Dict, Any, Optional
import time
from pathlib import Path

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.utils.docx_generator import generate_docx_report

def document_generation_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """LangGraph node that generates a DOCX document from the final response.
    
    Args:
        state: GraphState containing 'final_response'
        config: Runtime configuration
        
    Returns:
        State update with 'generated_document_path'
    """
    print("\n" + "="*80)
    print("📄 DOCUMENT GENERATION NODE")
    print("="*80)
    
    # Prefer the raw draft content if available (from Refinement Node), otherwise use final_response
    final_response = state.get("generated_document_content") or state.get("final_response")
    
    if not final_response:
        print("⚠️  No final response found to generate document from.")
        return {}
        
    try:
        # Create a unique filename based on timestamp
        timestamp = int(time.time())
        filename = f"output/response_{timestamp}.docx"
        
        # Ensure output directory exists (handled by generate_docx_report)
        
        print(f"Generating DOCX: {filename}")
        docx_path = generate_docx_report(final_response, filename)
        
        print(f"✅ Document generated successfully: {docx_path}")
        
        return {
            "generated_document_path": docx_path
        }
        
    except Exception as e:
        print(f"❌ Document generation failed: {e}")
        # We don't want to fail the whole graph if PDF generation fails
        return {}
