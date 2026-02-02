from pydantic import BaseModel, Field
from typing import Optional


class ExtractedEntity(BaseModel):
    name: str = Field(..., description="Entity name")
    entity_type: Optional[str] = Field(None, description="Entity type from EntityType enum")
    canonical_id: Optional[str] = Field(None, description="Canonical identifier (e.g., IPC:Section:420)")
    parent_id: Optional[str] = Field(None, description="Canonical id of parent entity, if known")
    hierarchy_level: Optional[int] = Field(None, description="Numeric hierarchy depth (1=top)")
    source: Optional[str] = Field(None, description="Source document or section")
    confidence: Optional[float] = Field(None, description="Extraction confidence 0.0-1.0")
