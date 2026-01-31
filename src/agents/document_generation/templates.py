from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class DocumentTemplate(BaseModel):
    """
    Represents a document template configuration.
    """
    template_id: str = Field(..., description="Unique identifier for the template")
    name: str = Field(..., description="Human-readable name of the template")
    description: str = Field(..., description="Description of use case")
    file_path: str = Field(..., description="Relative path to the .docx template file from project root")
    required_placeholders: List[str] = Field(default_factory=list, description="List of placeholder keys expected in the template")
    default_values: Dict[str, str] = Field(default_factory=dict, description="Default values for placeholders")

class TemplateRegistry:
    """
    Registry for managing available document templates.
    """
    _templates: Dict[str, DocumentTemplate] = {}

    @classmethod
    def register(cls, template: DocumentTemplate):
        cls._templates[template.template_id] = template

    @classmethod
    def get(cls, template_id: str) -> Optional[DocumentTemplate]:
        return cls._templates.get(template_id)

    @classmethod
    def list_templates(cls) -> List[DocumentTemplate]:
        return list(cls._templates.values())

# Initialize Registry with known templates
# Note: In a real app, this might load from a config file or DB.
# For now, we register the known "Bail Application" template.

# Placeholder list based on typical bail application needs. 
# We will verify the exact placeholders in the docx later, but for now we define what we expect.
bail_template = DocumentTemplate(
    template_id="bail_application",
    name="Bail Application",
    description="Standard bail application form for court submission",
    file_path="data/temapalates/bail_application.docx", # Keeping original typo path for now as per plan
    required_placeholders=[
        "COURT_NAME",
        "DISTRICT",
        "APPLICANT_NAME",
        "FATHER_NAME",
        "AGE",
        "RESIDENCE",
        "FIR_NUMBER",
        "POLICE_STATION",
        "OFFENCES", # Sections
        "DATE_OF_ARREST",
        "GROUNDS_FOR_BAIL", # This might be a list or a big text block
        "PRAYER"
    ]
)

TemplateRegistry.register(bail_template)
