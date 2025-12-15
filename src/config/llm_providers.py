"""
LLM Provider Abstraction Layer.

Provides a unified interface for different LLM providers (OpenAI, Gemini).
This allows agents to use different providers without code changes.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
import os
from dataclasses import dataclass


@dataclass
class LLMProviderConfig:
    """Base configuration for LLM providers."""
    api_key: str
    model: str
    temperature: float
    max_tokens: Optional[int] = None
    top_p: float = 1.0


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_llm(self, temperature: Optional[float] = None, **kwargs) -> Any:
        """
        Get the LLM instance for this provider.

        Args:
            temperature: Optional temperature override
            **kwargs: Additional provider-specific arguments

        Returns:
            LangChain ChatModel instance
        """
        pass

    @abstractmethod
    def get_client(self) -> Any:
        """Get the raw client instance for this provider."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (defaults to gpt-4o-mini)
            temperature: Temperature setting (defaults to 0.2)
            max_tokens: Maximum tokens in response
            top_p: Top-p sampling parameter
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please set it before initializing OpenAI provider."
            )

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self._client = None

    def get_client(self) -> Any:
        """Get OpenAI client instance."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def get_llm(self, temperature: Optional[float] = None, **kwargs) -> Any:
        """Get ChatOpenAI instance with structured output support."""
        from langchain_openai import ChatOpenAI

        temp = temperature if temperature is not None else self.temperature

        return ChatOpenAI(
            model=self.model,
            temperature=temp,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            **kwargs,
        )


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
    ):
        """Initialize Gemini provider.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Model name (defaults to gemini-2.0-flash)
            temperature: Temperature setting (defaults to 0.2)
            max_tokens: Maximum tokens in response
            top_p: Top-p sampling parameter
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Please set it before initializing Gemini provider."
            )

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self._client = None

    def get_client(self) -> Any:
        """Get Gemini client instance."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai
        return self._client

    def get_llm(self, temperature: Optional[float] = None, **kwargs) -> Any:
        """Get ChatGoogleGenerativeAI instance with structured output support."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        temp = temperature if temperature is not None else self.temperature

        return ChatGoogleGenerativeAI(
            model=self.model,
            temperature=temp,
            max_output_tokens=self.max_tokens,
            top_p=self.top_p,
            **kwargs,
        )


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }

    @classmethod
    def get_provider(
        cls,
        provider_name: str = "openai",
        **kwargs,
    ) -> BaseLLMProvider:
        """
        Get an LLM provider instance.

        Args:
            provider_name: Name of the provider ('openai' or 'gemini')
            **kwargs: Arguments to pass to the provider constructor

        Returns:
            BaseLLMProvider instance

        Raises:
            ValueError: If provider_name is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            supported = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Supported providers: {supported}"
            )
        return provider_class(**kwargs)

    @classmethod
    def get_provider_from_env(cls, prefix: str = "OPENAI") -> BaseLLMProvider:
        """
        Get provider based on environment variables.

        Args:
            prefix: Environment variable prefix (OPENAI, GEMINI, etc.)

        Returns:
            Configured BaseLLMProvider instance

        Raises:
            ValueError: If required environment variables are missing
        """
        provider_name = os.getenv("LLM_PROVIDER", "openai").lower()

        if provider_name == "openai":
            return cls.get_provider(
                "openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("RESEARCH_MODEL_NAME", "gpt-4o-mini"),
                temperature=float(os.getenv("RESEARCH_TEMPERATURE", "0.2")),
            )
        elif provider_name == "gemini":
            return cls.get_provider(
                "gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.2")),
            )
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {provider_name}. "
                f"Supported: openai, gemini"
            )
