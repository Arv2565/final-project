"""
Extended Pydantic model for legal document extraction including entities.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

from .extracted_entity import ExtractedEntity


class LegalDocumentKnowledgeV2(BaseModel):
    title: str = Field(description="The title of the legal document")
    purpose: str = Field(description="The stated purpose or objective of the document")
    scope: str = Field(description="The scope or applicability of the document")
    key_provisions: List[str] = Field(description="4-6 key operational provisions", min_items=4, max_items=6)
    administration: str = Field(description="Information about how the document is administered or enforced")

    # New optional field for extracted entities to support hierarchy
    entities: Optional[List[ExtractedEntity]] = Field(default=None, description="Optional extracted entities with hierarchy metadata")

    class Config:
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
                "administration": "Administered by the Ministry of Legal Affairs through...",
                "entities": [
                    {"name": "Section 5", "entity_type": "Section", "canonical_id": "IPC:Section:5"}
                ]
            }
        }
