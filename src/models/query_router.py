from pydantic import BaseModel, Field
from typing import Optional


class QueryMetadata(BaseModel):
    """Metadata extracted from user query by QueryRouterAgent."""
    
    language: Optional[str] = Field(
        None,
        description="ISO language code (e.g., 'en', 'hi', 'es')"
    )
    has_personal_data: bool = Field(
        False,
        description="Whether the query contains personal/sensitive information"
    )
    is_legal_question: bool = Field(
        False,
        description="Whether the query is related to legal matters"
    )


class QueryRouterOutput(BaseModel):
    """Output from QueryRouterAgent.
    
    The agent normalizes the query, translates to English if needed,
    and extracts basic metadata.
    """
    
    cleaned_query: str = Field(
        ...,
        description="Normalized and cleaned query, translated to English if originally in another language"
    )
    metadata: QueryMetadata = Field(
        ...,
        description="Extracted metadata about the query"
    )
