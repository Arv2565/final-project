"""
Unified Embedding Configuration and Service Setup.

This module centralizes all embedding-related configuration,
including both vector embeddings (Qdrant) and entity embeddings (Neo4j).
"""

from dataclasses import dataclass
from typing import Optional, Literal
import os

from .models import get_embedding_config, get_openai_client


@dataclass
class EmbeddingServiceConfig:
    """Configuration for embedding service initialization."""
    
    # Vector embedding service (Qdrant - HuggingFace InLegalBERT)
    vector_model_name: str
    vector_model_dimension: int
    vector_max_seq_length: int = 512
    vector_batch_size: int = 8
    vector_device: str = "auto"  # auto, cpu, cuda, mps
    
    # Entity embedding service (Neo4j - OpenAI text-embedding-3-large)
    entity_model_name: str
    entity_model_dimension: int
    
    # Batch processing
    embedding_batch_size: int = 8
    embedding_timeout: int = 300  # seconds


def get_embedding_service_config() -> EmbeddingServiceConfig:
    """
    Create embedding service configuration from environment and defaults.
    
    Returns:
        EmbeddingServiceConfig: Configuration for embedding services.
    """
    embedding_cfg = get_embedding_config()
    
    return EmbeddingServiceConfig(
        vector_model_name=embedding_cfg.vector_model_name,
        vector_model_dimension=embedding_cfg.vector_model_dimension,
        vector_max_seq_length=int(os.getenv("VECTOR_MAX_SEQ_LENGTH", "512")),
        vector_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "8")),
        vector_device=os.getenv("EMBEDDING_DEVICE", "auto"),
        entity_model_name=embedding_cfg.entity_embedding_model,
        entity_model_dimension=embedding_cfg.entity_embedding_dimension,
        embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "8")),
        embedding_timeout=int(os.getenv("EMBEDDING_TIMEOUT", "300")),
    )


def validate_embedding_environment() -> bool:
    """
    Validate that required environment variables for embeddings are set.
    
    Returns:
        bool: True if all required variables are set.
        
    Raises:
        ValueError: If critical environment variables are missing.
    """
    required_vars = ["OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise ValueError(
            f"Missing required environment variables for embeddings: {', '.join(missing)}"
        )
    
    return True
