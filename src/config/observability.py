"""
Observability configuration for the Legal AI Assistant.

This module handles the initialization of observability tools like Langfuse.
"""
import os
from typing import Optional

def get_langfuse_callback() -> Optional["CallbackHandler"]:
    """
    Initialize and return the LangfuseCallbackHandler.
    
    This function checks for the necessary environment variables.
    If they are present, it returns a configured handler.
    Otherwise, it checks if we are in a development environment where we might want to warn or skip.
    """
    from langfuse.langchain import CallbackHandler
    
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


def setup_observability() -> None:
    """
    Configure the global Langfuse client for decorator-based tracing.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    
    # If HOST is not set in env, the Langfuse SDK defaults to Cloud (https://cloud.langfuse.com).
    # However, this project defaults to localhost:3000. We must align them.
    if "LANGFUSE_HOST" not in os.environ:
        os.environ["LANGFUSE_HOST"] = host

    if public_key and secret_key:
        try:
            import langfuse
            # Instantiate a client to ensure environment variables are correctly picked up
            # and to validate credentials before the application starts.
            # This also helps ensure the global configuration is ready.
            c = langfuse.Langfuse()
            c.shutdown()
        except Exception as e:
            print(f"WARNING: Failed to initialize Langfuse: {e}")

    else:
        print("DEBUG: Langfuse credentials MISSING.")
