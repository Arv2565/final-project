import logging
from typing import Dict, Any
from pathlib import Path
from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.prompts.document_generation_prompts import PROCEDURE_GENERATION_SYSTEM_PROMPT
from pydantic import BaseModel, Field

class ProcedureOutput(BaseModel):
    procedure_text: str

class ProcedureGenerationAgent:
    """Generates procedural guidance for the document."""

    def __init__(self) -> None:
        self.llm = get_agent_llm(
            model_type="writer",
            output_schema=ProcedureOutput
        )
        self.templates_dir = Path(__file__).parent.parent.parent.parent / "data" / "templates"

    def __call__(self, procedure_filename: str, document_name: str, language_code: str = "en") -> str:
        """
        Generates/Refines procedural steps in the specified language.
        
        Args:
            procedure_filename: The filename of the template procedure
            document_name: Name of the document for context
            language_code: ISO language code (e.g., 'en', 'hi', 'ml') for output language
        
        Even though we have a static procedure file (a.txt), the prompt asks to:
        "Instruct the Procedure Agent to: Generate procedural steps... Use simple, neutral legal language..."
        
        But step 1 also says: "Map procedure_txt -> <alphabet>.txt"
        And constraint: "Save procedure text as <alphabet>.txt" (This suggests we might be WRITING it, or READING it?)
        
        Clarification from prompt:
        "Input: Procedure files must be named alphabetically: a.txt..."
        "Output Step 6: Save output as plain text in graph_state.procedure_text... File naming: Save procedure text as <alphabet>.txt"
        
        Wait, if the files already exist (a.txt, b.txt), maybe we just READ them?
        
        Re-reading Step 6:
        "Instruct the Procedure Agent to:
        - Generate procedural steps for the selected document
        - Use simple, neutral legal language
        - Include: a. Purpose, b. Parties...
        - Save output as plain text in: graph_state.procedure_text"
        
        It seems we should GENERATE the content dynamically using the LLM, possibly using the existing file as a base or context, OR completely generating it. Given we have "procedure files" as input, we probably read the raw file and have the LLM format/refine it, OR the input files are empty/dummy and we generate from scratch.
        
        Given the constraints "Do NOT hallucinate legal requirements", trusting the static file `a.txt` seems safer if it exists. 
        However, if `a.txt` is just a placeholder/dummy as per my plan, I should generate it.
        
        Let's assume `a.txt` contains the raw legal procedure and we use LLM to format it nicely into the required sections.
        """
        
        file_path = self.templates_dir / procedure_filename
        raw_content = ""
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    raw_content = f.read()
        except:
            pass # consistency with generating if missing
        
        # Map language code to language name
        language_map = {
            "en": "English",
            "hi": "Hindi",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "zh": "Chinese",
            "ta": "Tamil",
            "te": "Telugu",
            "kn": "Kannada",
            "ml": "Malayalam",
        }
        response_language = language_map.get(language_code, "English")
        
        system_prompt = PROCEDURE_GENERATION_SYSTEM_PROMPT.format(
            document_name=document_name, 
            raw_content=raw_content,
            response_language=response_language,
            language_code=language_code
        )
        
        try:
            result = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate procedure for: {document_name}"},
                ]
            )
            return result.procedure_text
        except Exception as e:
            logging.error(f"Procedure generation failed: {e}")
            raise
