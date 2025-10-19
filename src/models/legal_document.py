"""
Pydantic models for legal document knowledge extraction.
"""
from typing import List
from pydantic import BaseModel, Field


class LegalDocumentKnowledge(BaseModel):
    """
    Model for extracted legal document knowledge.
    
    This model represents the structured output from PDF legal document analysis,
    containing title, purpose, scope, key provisions, and administration details.
    """
    
    title: str = Field(
        description="The title of the legal document"
    )
    
    purpose: str = Field(
        description="The stated purpose or objective of the document"
    )
    
    scope: str = Field(
        description="The scope or applicability of the document"
    )
    
    key_provisions: List[str] = Field(
        description="4-6 key operational provisions with rule/section numbers where available",
        min_items=4,
        max_items=6
    )
    
    administration: str = Field(
        description="Information about how the document is administered or enforced"
    )

    class Config:
        """Configuration for the Pydantic model."""
        json_encoders = {
            # Custom encoders if needed
        }
        schema_extra = {
            "example": {
                "title": "Example Legal Act 2023",
                "purpose": "To regulate and provide framework for...",
                "scope": "Applies to all citizens within the jurisdiction of...",
                "key_provisions": [
                    "Section 5: Establishes regulatory authority",
                    "Section 12: Defines penalty structure",
                    "Section 18: Outlines appeal process",
                    "Section 25: Specifies implementation timeline"
                ],
                "administration": "Administered by the Ministry of Legal Affairs through..."
            }
        }