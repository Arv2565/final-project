"""
Configuration settings for the Legal Document Ingestion Workflow.

This module manages environment variables and settings for:
- Qdrant database connection
- inLegalBERT model configuration
- Document processing parameters
- Production-ready security settings
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class QdrantConfig:
    """Qdrant database configuration."""
    host: str
    port: int
    api_key: Optional[str] = None
    collection_name: str = "legal_documents"
    vector_size: int = 768  # inLegalBERT embedding size
    distance_metric: str = "cosine"
    
    @classmethod
    def from_env(cls) -> "QdrantConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            api_key=os.getenv("QDRANT_API_KEY"),
            collection_name=os.getenv("QDRANT_COLLECTION", "legal_documents"),
            vector_size=int(os.getenv("QDRANT_VECTOR_SIZE", "768")),
            distance_metric=os.getenv("QDRANT_DISTANCE_METRIC", "cosine")
        )

@dataclass
class EmbeddingConfig:
    """inLegalBERT embedding model configuration."""
    model_name: str = "nlpaueb/legal-bert-base-uncased"
    max_token_length: int = 512
    batch_size: int = 8
    device: str = "auto"  # auto, cpu, cuda
    
    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """Load configuration from environment variables."""
        return cls(
            model_name=os.getenv("LEGAL_BERT_MODEL", "nlpaueb/legal-bert-base-uncased"),
            max_token_length=int(os.getenv("MAX_TOKEN_LENGTH", "512")),
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "8")),
            device=os.getenv("EMBEDDING_DEVICE", "auto")
        )

@dataclass
class ProcessingConfig:
    """Document processing configuration."""
    chunk_size: int = 450  # Leave buffer for special tokens
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    supported_pdf_extensions: tuple = (".pdf",)
    supported_json_extensions: tuple = (".json",)
    
    @classmethod
    def from_env(cls) -> "ProcessingConfig":
        """Load configuration from environment variables."""
        return cls(
            chunk_size=int(os.getenv("CHUNK_SIZE", "450")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            min_chunk_size=int(os.getenv("MIN_CHUNK_SIZE", "100"))
        )

@dataclass
class Neo4jConfig:
    """Neo4j graph database configuration."""
    uri: str
    user: str
    password: str
    database: str = "neo4j"
    
    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Load configuration from environment variables."""
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )

@dataclass
class SecurityConfig:
    """Security and compliance configuration."""
    log_sensitive_data: bool = False
    data_retention_days: Optional[int] = None
    encryption_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Load security configuration from environment variables."""
        return cls(
            log_sensitive_data=os.getenv("LOG_SENSITIVE_DATA", "false").lower() == "true",
            data_retention_days=int(os.getenv("DATA_RETENTION_DAYS")) if os.getenv("DATA_RETENTION_DAYS") else None,
            encryption_key=os.getenv("DATA_ENCRYPTION_KEY")
        )

class Settings:
    """Main settings class combining all configurations."""
    
    def __init__(self):
        self.qdrant = QdrantConfig.from_env()
        self.embedding = EmbeddingConfig.from_env()
        self.processing = ProcessingConfig.from_env()
        self.security = SecurityConfig.from_env()
        self.neo4j = Neo4jConfig.from_env()
        
        # Metadata field mapping for legal documents
        self.metadata_fields = {
            "court": "string",
            "date": "datetime", 
            "case_number": "string",
            "title": "string",
            "file_type": "string",
            "jurisdiction": "string",
            "case_type": "string",
            "judges": "string",
            "parties": "string",
            "source_file": "string",
            "chunk_id": "integer",
            "total_chunks": "integer",
            "processing_timestamp": "datetime"
        }
    
    def get_indexed_fields(self) -> Dict[str, Any]:
        """Get fields that should be indexed in Qdrant for filtering."""
        return {
            "court": True,
            "date": True,
            "case_type": True,
            "jurisdiction": True,
            "file_type": True
        }
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        # Check required Qdrant settings
        if not self.qdrant.host:
            raise ValueError("QDRANT_HOST is required")
        
        # Check embedding model availability
        if not self.embedding.model_name:
            raise ValueError("LEGAL_BERT_MODEL is required")
        
        # Validate chunk size vs token limit
        if self.processing.chunk_size >= self.embedding.max_token_length:
            raise ValueError(f"Chunk size ({self.processing.chunk_size}) must be less than max token length ({self.embedding.max_token_length})")
        
        return True

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings

def validate_environment() -> bool:
    """Validate that all required environment variables are set."""
    try:
        settings.validate()
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False