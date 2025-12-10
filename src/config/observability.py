"""
Observability configuration for the Legal AI Assistant.

This module handles the initialization of observability tools like Langfuse.
"""
import os
from typing import Optional
from langfuse.langchain import CallbackHandler

def get_langfuse_callback() -> Optional[CallbackHandler]:
    """
    Initialize and return the LangfuseCallbackHandler.
    
    This function checks for the necessary environment variables.
    If they are present, it returns a configured handler.
    Otherwise, it checks if we are in a development environment where we might want to warn or skip.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    
    if public_key and secret_key:
        return CallbackHandler(
            public_key=public_key
        )
    
    # If keys are missing, we can log a warning or just return None (to run without tracing)
    print("WARNING: Langfuse credentials not found. Running without observability.")
    return None
