"""
Document Ingestion Pipeline.

Handles Step 1-3 of the ingestion process:
1. Extract and preprocess legal documents (PDF/JSON)
2. Generate embeddings using inLegalBERT
3. Store embeddings with metadata in Qdrant
"""

from .pipeline import LegalDocumentIngestionWorkflow, IngestionResult, FileProcessingResult

__all__ = [
    "LegalDocumentIngestionWorkflow",
    "IngestionResult",
    "FileProcessingResult",
]
