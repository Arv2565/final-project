"""
LangChain agent for legal document knowledge extraction.
"""
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser
from langchain.chains import LLMChain
from pydantic import ValidationError

from src.models.legal_document_v2 import LegalDocumentKnowledgeV2 as LegalDocumentKnowledge
from src.utils.pdf import PDFTextExtractor


logger = logging.getLogger(__name__)


class LegalKnowledgeOutputParser(BaseOutputParser[LegalDocumentKnowledge]):
    """Custom output parser for legal document knowledge extraction."""
    
    def parse(self, text: str) -> LegalDocumentKnowledge:
        """Parse the LLM output into a LegalDocumentKnowledge object."""
        try:
            # Try to extract JSON from the response
            text = text.strip()
            
            # Handle cases where the response might have extra text
            if text.startswith('```json'):
                text = text[7:]  # Remove ```json
            if text.endswith('```'):
                text = text[:-3]  # Remove ```
                
            # Find JSON object in the text
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_text = text[json_start:json_end]
                parsed_data = json.loads(json_text)
                # Ensure keys conform; entities is optional
                return LegalDocumentKnowledge(**parsed_data)
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.error(f"Failed to parse LLM output: {e}")
            logger.error(f"Raw output: {text}")
            # Return a fallback object
            return LegalDocumentKnowledge(
                title="information not publicly available",
                purpose="information not publicly available", 
                scope="information not publicly available",
                key_provisions=["information not publicly available"] * 4,
                administration="information not publicly available",
                entities=None
            )


class LegalDocumentKnowledgeExtractor:
    """
    LangChain agent for extracting structured knowledge from legal documents.
    
    Uses the exact prompt specification provided for consistent extraction
    of title, purpose, scope, key provisions, and administration details.
    """
    
    EXTRACTION_PROMPT = """You are a legal knowledge extraction model. Read only the provided PDF file contents and produce one JSON object with exactly these fields and types:

{
"title": "string",
"purpose": "string", 
"scope": "string",
"key_provisions": ["string", "..."], // 4–6 separate items; each item short, precise, and grounded in the PDF (no interpretation)
"administration": "string",
"entities": [
  {
    "name": "string",
    "entity_type": "EntityType enum value (optional)",
    "canonical_id": "string (optional, e.g., IPC:Section:420)",
    "parent_id": "string (optional canonical id of parent)",
    "hierarchy_level": "integer (optional; 1=top)",
    "source": "string (optional source/location)",
    "confidence": "float (0.0-1.0)"
  }
]
}

Rules (must be followed by the model, verbatim):

Derive content only from the PDF provided. Do not use outside knowledge. If a fact is not explicitly present in the PDF, put exactly: "information not publicly available".

Preserve factual precision. Do not paraphrase in a way that changes legal meaning.

The key_provisions array must contain 4–6 distinct, operational provisions (cite rule/section numbers or exact wording from the PDF where available). When a provision mentions "procedures," "schemes," "committees," or similar, identify the procedure or scheme and include any form numbers, rule numbers, tribunal names, committee composition, timelines, or application channels shown in the PDF.

If the PDF does not supply any content for a required field, set that field value to "information not publicly available".

Return only valid JSON for a single object (no commentary, no surrounding text). If you are given multiple PDFs, return a JSON array of objects (one object per PDF).

Validate the JSON shape exactly as the schema above; mis-typed keys or extra fields will be rejected. Extra keys are allowed only if they conform to the documented schema above (entities is optional).

Extracted text may contain quoted phrases; keep quotes only if they appear verbatim in the PDF.

If the PDF is in a language other than English, translate extracted fields to English but indicate this by appending (translated) after each translated field.

PDF Content:
{pdf_content}

JSON Response:"""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize the legal document knowledge extractor.
        
        Args:
            gemini_api_key: Gemini API key. If None, it will be retrieved from the 'GEMINI_API_KEY' environment variable.
        """
        self.pdf_extractor = PDFTextExtractor()
        self.output_parser = LegalKnowledgeOutputParser()
        
        # Get API key from environment if not provided
        if not gemini_api_key:
            gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY not found in arguments or environment variables.")
            raise ValueError("GEMINI_API_KEY must be provided or set as an environment variable.")
        
        # Initialize LLM
        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",  # Using the latest powerful model
                temperature=0,  # Use deterministic output
                google_api_key=gemini_api_key
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            raise
        
        # Create prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["pdf_content"],
            template=self.EXTRACTION_PROMPT
        )
        
        # Create LLM chain
        self.extraction_chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt_template,
            output_parser=self.output_parser
        )
        
        logger.info("Legal document knowledge extractor initialized")
    
    def extract_from_pdf(self, pdf_path: Path) -> Optional[LegalDocumentKnowledge]:
        """
        Extract structured knowledge from a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            LegalDocumentKnowledge object or None if extraction fails
        """
        try:
            # Extract text from PDF
            logger.info(f"Extracting text from PDF: {pdf_path}")
            pdf_content = self.pdf_extractor.extract_text_from_pdf(pdf_path)
            
            if not pdf_content:
                logger.error(f"Failed to extract text from PDF: {pdf_path}")
                return None
            
            # Truncate content if too long. Gemini-Pro has a large context, but we'll set a generous limit.
            if len(pdf_content) > 100000:  # Rough character limit for ~25k tokens
                logger.warning(f"PDF content too long ({len(pdf_content)} chars), truncating to 100,000 characters.")
                pdf_content = pdf_content[:100000] + "...\n[CONTENT TRUNCATED DUE TO LENGTH]"
            
            # Run extraction
            logger.info("Running LangChain extraction")
            result = self.extraction_chain.run(pdf_content=pdf_content)
            
            logger.info(f"Successfully extracted knowledge from {pdf_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting knowledge from PDF {pdf_path}: {e}")
            return None
    
    def extract_from_directory(self, directory_path: Path, recursive: bool = True) -> List[tuple[Path, LegalDocumentKnowledge]]:
        """
        Extract knowledge from all PDF files in a directory.
        
        Args:
            directory_path: Path to directory containing PDF files
            recursive: Whether to search subdirectories
            
        Returns:
            List of tuples (pdf_path, extracted_knowledge)
        """
        results = []
        
        try:
            # Find all PDF files
            if recursive:
                pdf_files = list(directory_path.rglob("*.pdf"))
            else:
                pdf_files = list(directory_path.glob("*.pdf"))
            
            logger.info(f"Found {len(pdf_files)} PDF files to process")
            
            for pdf_file in pdf_files:
                logger.info(f"Processing: {pdf_file.name}")
                
                knowledge = self.extract_from_pdf(pdf_file)
                if knowledge:
                    results.append((pdf_file, knowledge))
                    logger.info(f"✅ Successfully processed: {pdf_file.name}")
                else:
                    logger.warning(f"❌ Failed to process: {pdf_file.name}")
            
            logger.info(f"Processed {len(results)} out of {len(pdf_files)} PDF files")
            
        except Exception as e:
            logger.error(f"Error processing directory {directory_path}: {e}")
        
        return results
    
    def save_results_to_json(self, results: List[tuple[Path, LegalDocumentKnowledge]], output_path: Path) -> None:
        """
        Save extraction results to a JSON file.
        
        Args:
            results: List of (pdf_path, knowledge) tuples
            output_path: Path to save JSON results
        """
        try:
            output_data = []
            
            for pdf_path, knowledge in results:
                entry = {
                    "source_file": str(pdf_path),
                    "file_name": pdf_path.name,
                    **knowledge.dict()
                }
                output_data.append(entry)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(output_data)} results to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving results to {output_path}: {e}")