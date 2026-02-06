import logging
from typing import Dict, List
from pathlib import Path
from pydantic import BaseModel, Field

from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.document_generation_prompts import DOCUMENT_GENERATION_SYSTEM_PROMPT

class DocumentOutput(BaseModel):
    content: str = Field(description="The complete generated markdown document.")

class DocumentGenerationAgent:
    """Generates the final document by replacing placeholders with user input using an LLM."""

    def __init__(self) -> None:
        self.templates_dir = Path(__file__).parent.parent.parent.parent / "data" / "templates"
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=DocumentOutput
        )

    def generate(self, template_filename: str, placeholders: List[dict], user_response: str) -> str:
        """
        Generates the document by calling the LLM.
        
        Args:
            template_filename: Name of the template file.
            placeholders: List of placeholder dicts (from extraction step).
            user_response: Free-text response from the user.
        """
        file_path = self.templates_dir / template_filename
        try:
            with open(file_path, 'r') as f:
                template_content = f.read()
        except Exception as e:
            logging.error(f"Failed to read template file {file_path}: {e}")
            raise

        # Prepare placeholders list for the prompt
        placeholders_list = [p['key'] for p in placeholders]
        
        system_prompt = DOCUMENT_GENERATION_SYSTEM_PROMPT
        
        user_prompt = f"""Template Content:
{template_content}

Placeholders List:
{placeholders_list}

User Response:
"{user_response}"
"""
        
        try:
            result = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return result.content
        except Exception as e:
            logging.error(f"Document generation failed: {e}")
            raise

    def __call__(self, template_filename: str, placeholders: List[dict], user_response: str) -> str:
        """Wrapper for generate method."""
        return self.generate(template_filename, placeholders, user_response)
