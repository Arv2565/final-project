"""
Agent LLM initialization helper.

Provides utilities for agents to get the appropriate LLM instance
based on the selected provider (OpenAI or Gemini).
"""

from typing import Optional, Type, Any
import os
from src.config import get_llm_config


def get_agent_llm(
    model_type: str = "writer",
    output_schema: Optional[Type] = None,
) -> Any:
    """
    Get an LLM instance for an agent based on configured provider.

    Args:
        model_type: Type of model - 'research', 'writer', or 'chat'
        output_schema: Optional Pydantic model for structured output

    Returns:
        LangChain LLM instance (ChatOpenAI or ChatGoogleGenerativeAI)
        with optional structured output binding

    Raises:
        ValueError: If configured provider is not supported
    """
    config = get_llm_config()

    if config.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Please set it before using Gemini provider."
            )

        # Select model and temperature based on type
        if model_type == "research":
            model = config.gemini_research_model
            temperature = config.gemini_temperature_research
        elif model_type == "chat":
            model = config.gemini_chat_model
            temperature = config.gemini_temperature_chat
        else:  # Default to writer
            model = config.gemini_writer_model
            temperature = config.gemini_temperature_writer

        llm = ChatGoogleGenerativeAI(
            model=model,
            api_key=api_key,
            temperature=temperature,
            top_p=config.top_p,
            max_output_tokens=config.max_tokens,
        )

    else:  # Default to OpenAI
        from langchain_openai import ChatOpenAI

        # Select model and temperature based on type
        if model_type == "research":
            model = config.research_model
            temperature = config.temperature_research
        elif model_type == "chat":
            model = config.chat_model
            temperature = config.temperature_chat
        else:  # Default to writer
            model = config.writer_model
            temperature = config.temperature_writer

        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            top_p=config.top_p,
            max_tokens=config.max_tokens,
        )

    # Apply structured output binding if schema provided
    if output_schema:
        llm = llm.with_structured_output(output_schema)

    return llm
