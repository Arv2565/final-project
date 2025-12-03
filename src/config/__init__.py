"""
Configuration module for Legal AI Assistant.

Centralizes all configuration including:
- LLM and embedding model configuration
- Database connection settings (Qdrant, Neo4j)
- Document processing parameters
- Security and compliance settings
- Legal domain ontology
"""

from .models import (
    LLMConfig,
    EmbeddingModelConfig,
    get_llm_config,
    get_embedding_config,
    get_openai_client,
    get_model_config,  # Backward compatibility
)

from .settings import (
    QdrantConfig,
    EmbeddingConfig,
    ProcessingConfig,
    SecurityConfig,
    Settings,
    get_settings,
    validate_environment,
)

from .embeddings import (
    EmbeddingServiceConfig,
    get_embedding_service_config,
    validate_embedding_environment,
)

from .ontology import (
    EntityType,
    RelationType,
    LegalOntology,
)

__all__ = [
    # LLM Configuration
    "LLMConfig",
    "EmbeddingModelConfig",
    "get_llm_config",
    "get_embedding_config",
    "get_openai_client",
    "get_model_config",  # Backward compatibility
    
    # System Configuration
    "QdrantConfig",
    "EmbeddingConfig",
    "ProcessingConfig",
    "SecurityConfig",
    "Settings",
    "get_settings",
    "validate_environment",
    
    # Embedding Configuration
    "EmbeddingServiceConfig",
    "get_embedding_service_config",
    "validate_embedding_environment",
    
    # Domain Ontology
    "EntityType",
    "RelationType",
    "LegalOntology",
]
