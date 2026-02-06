import json
import logging
from typing import Dict, Any, List
from pathlib import Path

from src.models import TemplateInfo
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.document_generation_prompts import TEMPLATE_SELECTION_SYSTEM_PROMPT

class TemplateSelectionAgent:
    """Selects the appropriate legal document template based on user query."""

    def __init__(self) -> None:
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=TemplateInfo,
        )
        self.templates_path = Path(__file__).parent.parent.parent.parent / "data" / "templates" / "templates.json"
        
    def _load_templates(self) -> str:
        try:
           with open(self.templates_path, 'r') as f:
               templates = json.load(f)
               return json.dumps(templates, indent=2)
        except Exception as e:
            logging.error(f"Failed to load templates from {self.templates_path}: {e}")
            raise

    def __call__(self, query: str) -> TemplateInfo:
        """
        Selects the best template for the given query.
        """
        templates_json = self._load_templates()
        
        system_prompt = TEMPLATE_SELECTION_SYSTEM_PROMPT.format(templates_json=templates_json)
        
        user_prompt = f"User Request: {query}"
        
        try:
            result = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return result
        except Exception as e:
            logging.error(f"Template selection failed: {e}")
            raise
