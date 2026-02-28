from pydantic import BaseModel, Field
from typing import Optional


class QueryMetadata(BaseModel):
    """Metadata extracted from user query by QueryRouterAgent."""
    
    original_language: Optional[str] = Field(
        None,
        description="Original language detected in user query (ISO language code, e.g., 'en', 'hi', 'es', 'ml')"
    )
    language: Optional[str] = Field(
        None,
        description="Language after translation: always 'en' (English) if originally in another language, or original language code if already English"
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
