from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


class IntentType(str, Enum):
    """Legal query intent categories."""
    
    ASK_PROCEDURE = "ask_procedure"
    ASK_LAW_EXPLANATION = "ask_law_explanation"
    ASK_CASE_REFERENCE = "ask_case_reference"
    ASK_LAW_MAPPING = "ask_law_mapping"
    ASK_DRAFT = "ask_draft"
    ASK_COMPARISON = "ask_comparison"
    GENERAL_QUESTION = "general_question"
    CHIT_CHAT = "chit_chat"


class ExtractedEntities(BaseModel):
    """Entities extracted from legal query."""
    
    jurisdiction: Optional[str] = Field(
        None,
        description="Legal jurisdiction (e.g., 'India', 'US', 'EU')"
    )
    topic: Optional[str] = Field(
        None,
        description="Legal topic or area (e.g., 'divorce', 'company registration')"
    )
    time_frame: Optional[str] = Field(
        None,
        description="Temporal context: 'past', 'future', or 'unspecified'"
    )


class IntentClassifierOutput(BaseModel):
    """Output from IntentClassifierAgent.
    
    Classifies the user's intent and extracts relevant legal entities.
    """
    
    intent: IntentType = Field(
        ...,
        description="Classified intent category"
    )
    entities: ExtractedEntities = Field(
        ...,
        description="Extracted legal entities from the query"
    )
