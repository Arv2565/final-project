import re
import logging
from typing import List, Dict, Any
from pathlib import Path

from src.models.document_generation import PlaceholderInfo
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from pydantic import BaseModel, Field
from src.prompts.document_generation_prompts import PLACEHOLDER_EXTRACTION_SYSTEM_PROMPT

class ExtractedPlaceholders(BaseModel):
    placeholders: List[PlaceholderInfo]

class PlaceholderExtractionAgent:
    """Extracts placeholders from a document template."""

    def __init__(self) -> None:
       self.llm = get_agent_llm(
           model_type="writer",
           output_schema=ExtractedPlaceholders
       )
       self.templates_dir = Path(__file__).parent.parent.parent.parent / "data" / "templates"

    def __call__(self, template_filename: str) -> List[PlaceholderInfo]:
        """
        Reads the template file and extracts placeholders.
        """
        file_path = self.templates_dir / template_filename
        try:
            with open(file_path, 'r') as f:
                template_content = f.read()
        except Exception as e:
            logging.error(f"Failed to read template file {file_path}: {e}")
            raise

        system_prompt = PLACEHOLDER_EXTRACTION_SYSTEM_PROMPT
        
        user_prompt = f"Template Content:\n\n{template_content}"
        
        try:
            result = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return result.placeholders
        except Exception as e:
            logging.error(f"Placeholder extraction failed: {e}")
            raise
