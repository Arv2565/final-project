"""
LLM and Embedding Model Configuration.

Centralizes all model configurations including:
- Research and Writer agent models
- Chat model for GraphRAG
- Embedding models (Qdrant vectors and Neo4j entity embeddings)
- Temperature and other generation parameters
"""

from dataclasses import dataclass
import os
from typing import Optional

from openai import OpenAI


@dataclass
class LLMConfig:
    """Configuration for LLM models used by LangGraph agents and GraphRAG."""

    # LangGraph agent models - defaults to gpt-4o-mini (updated from gpt-4.1-mini)
    research_model: str = os.getenv("RESEARCH_MODEL_NAME", "gpt-4o-mini")
    writer_model: str = os.getenv("WRITER_MODEL_NAME", "gpt-4o-mini")
    
    # GraphRAG chat model for triple extraction
    chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    
    # Temperature settings
    temperature_research: float = float(os.getenv("RESEARCH_TEMPERATURE", "0.2"))
    temperature_writer: float = float(os.getenv("WRITER_TEMPERATURE", "0.4"))
    temperature_chat: float = float(os.getenv("CHAT_TEMPERATURE", "0.2"))
    
    # Model-specific parameters
    max_tokens: Optional[int] = None
    top_p: float = 1.0


@dataclass
class EmbeddingModelConfig:
    """Configuration for embedding models across the system."""

    # Vector embeddings for Qdrant (Step 2 of ingestion pipeline)
    vector_model_name: str = os.getenv("LEGAL_BERT_MODEL", "nlpaueb/legal-bert-base-uncased")
    vector_model_dimension: int = int(os.getenv("VECTOR_EMBEDDING_DIM", "768"))
    
    # Entity embeddings for Neo4j GraphRAG indexing
    entity_embedding_model: str = os.getenv("ENTITY_EMBEDDING_MODEL", "text-embedding-3-large")
    entity_embedding_dimension: int = int(os.getenv("ENTITY_EMBEDDING_DIM", "3072"))


# Singletons for configuration and client instances
_llm_config: Optional[LLMConfig] = None
_embedding_config: Optional[EmbeddingModelConfig] = None
_openai_client: Optional[OpenAI] = None


def get_llm_config() -> LLMConfig:
    """Return a singleton LLMConfig instance."""
    global _llm_config
    if _llm_config is None:
        _llm_config = LLMConfig()
    return _llm_config


def get_embedding_config() -> EmbeddingModelConfig:
    """Return a singleton EmbeddingModelConfig instance."""
    global _embedding_config
    if _embedding_config is None:
        _embedding_config = EmbeddingModelConfig()
    return _embedding_config


def get_openai_client() -> OpenAI:
    """Return a singleton OpenAI client.

    Relies on OPENAI_API_KEY being set in the environment.
    
    Raises:
        ValueError: If OPENAI_API_KEY is not set.
    """
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please set it before initializing OpenAI client."
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# Backward compatibility
def get_model_config() -> LLMConfig:
    """Deprecated: Use get_llm_config() instead."""
    return get_llm_config()
