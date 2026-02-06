from typing import TypedDict, List, Dict, Optional
from pydantic import BaseModel, Field

class TemplateInfo(BaseModel):
    """Information about a selected document template."""
    id: str = Field(..., description="Unique identifier for the template")
    name: str = Field(..., description="Display name of the template")
    index: int = Field(..., description="Index of the template file (1-based)")
    template_file: str = Field(..., description="Filename of the template text (e.g., '1.txt')")
    procedure_file: str = Field(..., description="Filename of the procedure text (e.g., 'a.txt')")

class PlaceholderInfo(BaseModel):
    """Information about a placeholder in the template."""
    key: str = Field(..., description="Normalized key for the placeholder (e.g., 'monthly_rent')")
    description: Optional[str] = Field(None, description="Description or original text of the placeholder")
    original_text: str = Field(..., description="The exact text found in the template")

class DocumentGenerationState(TypedDict, total=False):
    """
    State-specific to the Document Generation workflow.
    """
    # Step 1: Template Selection
    selected_template: Optional[TemplateInfo]
    
    # Step 2: Placeholder Extraction
    placeholders: Optional[List[PlaceholderInfo]]
    
    # Step 3: User Input
    # Maps placeholder key -> user provided value
    user_inputs: Optional[Dict[str, str]]
    
    # Step 5: Document Generation
    generated_document: Optional[str] # The markdown document with values filled
    
    # Step 6: Procedure Generation
    generated_procedure: Optional[str] # The procedural steps text
    
    # Status
    status: str # "selecting_template", "extracting_placeholders", "waiting_for_input", "generating", "completed"
