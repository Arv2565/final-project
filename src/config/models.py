"""
LLM and Embedding Model Configuration.

Centralizes all model configurations including:
- Research and Writer agent models
- Chat model for GraphRAG
- Embedding models (Qdrant vectors and Neo4j entity embeddings)
- Temperature and other generation parameters
- LLM provider selection (OpenAI, Gemini)
"""

from dataclasses import dataclass
import os
from typing import Optional

from openai import OpenAI


@dataclass
class LLMConfig:
    """Configuration for LLM models used by LangGraph agents and GraphRAG."""

    # LLM Provider selection (openai or gemini)
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # OpenAI Models
    research_model: str = os.getenv("RESEARCH_MODEL_NAME", "gpt-4o-mini")
    writer_model: str = os.getenv("WRITER_MODEL_NAME", "gpt-4o-mini")
    chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    
    # Gemini Models
    gemini_research_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    gemini_writer_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    gemini_chat_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    
    # Temperature settings
    temperature_research: float = float(os.getenv("RESEARCH_TEMPERATURE", "0.2"))
    temperature_writer: float = float(os.getenv("WRITER_TEMPERATURE", "0.4"))
    temperature_chat: float = float(os.getenv("CHAT_TEMPERATURE", "0.2"))
    
    # Gemini-specific temperature settings (can override defaults)
    gemini_temperature_research: float = float(os.getenv("GEMINI_TEMPERATURE_RESEARCH", os.getenv("RESEARCH_TEMPERATURE", "0.2")))
    gemini_temperature_writer: float = float(os.getenv("GEMINI_TEMPERATURE_WRITER", os.getenv("WRITER_TEMPERATURE", "0.4")))
    gemini_temperature_chat: float = float(os.getenv("GEMINI_TEMPERATURE_CHAT", os.getenv("CHAT_TEMPERATURE", "0.2")))
    
    # Model-specific parameters
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    
    def get_research_model(self) -> str:
        """Get the research model based on selected provider."""
        if self.llm_provider == "gemini":
            return self.gemini_research_model
        return self.research_model
    
    def get_writer_model(self) -> str:
        """Get the writer model based on selected provider."""
        if self.llm_provider == "gemini":
            return self.gemini_writer_model
        return self.writer_model
    
    def get_chat_model(self) -> str:
        """Get the chat model based on selected provider."""
        if self.llm_provider == "gemini":
            return self.gemini_chat_model
        return self.chat_model
    
    def get_research_temperature(self) -> float:
        """Get the research temperature based on selected provider."""
        if self.llm_provider == "gemini":
            return self.gemini_temperature_research
        return self.temperature_research
    
    def get_writer_temperature(self) -> float:
        """Get the writer temperature based on selected provider."""
        if self.llm_provider == "gemini":
            return self.gemini_temperature_writer
        return self.temperature_writer
    
    def get_chat_temperature(self) -> float:
        """Get the chat temperature based on selected provider."""
        if self.llm_provider == "gemini":
            return self.gemini_temperature_chat
        return self.temperature_chat


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


def get_llm_provider():
    """Get the configured LLM provider based on configuration.
    
    Returns:
        BaseLLMProvider instance (OpenAIProvider or GeminiProvider)
    """
    from .llm_providers import LLMProviderFactory
    
    config = get_llm_config()
    
    if config.llm_provider == "gemini":
        return LLMProviderFactory.get_provider(
            "gemini",
            api_key=os.getenv("GEMINI_API_KEY"),
            model=config.get_chat_model(),
            temperature=config.get_chat_temperature(),
        )
    else:  # Default to OpenAI
        return LLMProviderFactory.get_provider(
            "openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            model=config.get_chat_model(),
            temperature=config.get_chat_temperature(),
        )
