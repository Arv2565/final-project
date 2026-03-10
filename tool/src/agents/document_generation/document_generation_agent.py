import logging
import re
from typing import List
from pathlib import Path
from pydantic import BaseModel, Field

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

    def _normalize_generated_document(self, text: str) -> str:
        """Apply lightweight safety normalization for legal document formatting."""
        if not text:
            return text

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # Repair merged sub-clause markers after "as follows" style headings.
        normalized = re.sub(r"(?i)(as\s+follows)\s*([a-z])\.", r"\1:\n\2.", normalized)

        # Unwrap sentence-level hard wraps while preserving legal structure boundaries.
        normalized = self._unwrap_soft_line_breaks(normalized)

        # Keep internal line content but strip accidental leading indentation.
        normalized = "\n".join(line.lstrip() for line in normalized.split("\n"))

        # Avoid excessive blank lines.
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        return normalized.strip()

    def _is_structural_line(self, line: str) -> bool:
        """Return True when a line should remain a hard boundary in legal text."""
        stripped = line.strip()
        if not stripped:
            return False

        if re.match(r"^\d+\s*[-.)]\s+", stripped):
            return True
        if re.match(r"^[a-zA-Z]\s*[.)]\s+", stripped):
            return True

        heading_prefixes = (
            "To",
            "Dear Sir",
            "Dear Sir/Madam",
            "Place",
            "Ref",
            "LEGAL NOTICE",
            "ADVOCATE",
            "IN WITNESS",
        )
        if stripped.startswith(heading_prefixes):
            return True

        if re.match(r"^[A-Z][A-Z\s.&/-]{4,}$", stripped):
            return True

        return False

    def _should_join_lines(self, prev_line: str, next_line: str, in_address_block: bool) -> bool:
        """Join only when newline is likely an unwanted sentence wrap."""
        prev = prev_line.rstrip()
        nxt = next_line.lstrip()
        if not prev or not nxt:
            return False

        if in_address_block:
            return False

        if self._is_structural_line(next_line):
            return False

        # Keep major headings and salutation boundaries as separate lines.
        if re.match(r"(?i)^(to,?|dear\s+sir(?:/madam)?[, ]*|place[: ]|ref\.?|legal\s+notice|advocate|in\s+witness)", prev.strip()):
            return False
        if re.match(r"^[A-Z][A-Z\s.&/-]{4,}$", prev.strip()):
            return False

        if re.search(r":\s*$", prev) and re.match(r"^[a-zA-Z]\s*[.)]\s+", nxt):
            return False

        continuation_endings = re.compile(
            r"(?i)(M/s\.?|and|or|as|of|to|from|for|with|under|in|on|at|through|its|the|by|which|that)\s*$"
        )
        if continuation_endings.search(prev):
            return True

        if re.search(r"[,;]\s*$", prev):
            return True

        if not re.search(r"[.!?:]\s*$", prev):
            return True

        return False

    def _unwrap_soft_line_breaks(self, text: str) -> str:
        """Collapse soft wraps but keep legal sections, clauses, and address blocks intact."""
        lines = text.split("\n")
        output: List[str] = []
        i = 0
        in_address_block = False

        while i < len(lines):
            current = lines[i]
            stripped = current.strip()

            if re.match(r"(?i)^to,?$", stripped):
                in_address_block = True
            elif re.match(r"(?i)^dear\s+sir", stripped):
                in_address_block = False

            while i + 1 < len(lines) and self._should_join_lines(current, lines[i + 1], in_address_block):
                current = current.rstrip() + " " + lines[i + 1].lstrip()
                i += 1

            output.append(current)
            i += 1

        return "\n".join(output)

    def generate(self, template_filename: str, placeholders: List[dict], user_response: str, language_code: str = "en") -> str:
        """
        Generates the document by calling the LLM.
        
        Args:
            template_filename: Name of the template file.
            placeholders: List of placeholder dicts (from extraction step).
            user_response: Free-text response from the user.
            language_code: ISO language code (e.g., 'en', 'hi', 'ml') for document language.
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
        output_language = language_map.get(language_code, "English")
        
        system_prompt = DOCUMENT_GENERATION_SYSTEM_PROMPT
        
        user_prompt = f"""Output Language: {output_language} (language code: {language_code})

Template Content:
{template_content}

Placeholders List:
{placeholders_list}

User Response:
"{user_response}"

IMPORTANT: Generate the entire document in {output_language}, not in English.
"""
        
        try:
            result = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return self._normalize_generated_document(result.content)
        except Exception as e:
            logging.error(f"Document generation failed: {e}")
            raise

    def __call__(self, template_filename: str, placeholders: List[dict], user_response: str, language_code: str = "en") -> str:
        """Wrapper for generate method."""
        return self.generate(template_filename, placeholders, user_response, language_code)
