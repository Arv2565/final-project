"""
PDF text extraction utilities for legal documents.
"""
import logging
from pathlib import Path
from typing import Optional

import PyPDF2


logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """
    Utility class for extracting text from PDF files.
    
    Optimized for legal documents with comprehensive error handling
    and text cleaning capabilities.
    """
    
    def __init__(self):
        """Initialize the PDF text extractor."""
        pass
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text as string, or None if extraction fails
        """
        try:
            if not pdf_path.exists():
                logger.error(f"PDF file not found: {pdf_path}")
                return None
            
            if not pdf_path.suffix.lower() == '.pdf':
                logger.error(f"File is not a PDF: {pdf_path}")
                return None
            
            text_content = []
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                logger.info(f"Processing PDF with {len(pdf_reader.pages)} pages")
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(page_text)
                            logger.debug(f"Extracted text from page {page_num + 1}")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                        continue
            
            if not text_content:
                logger.error(f"No text could be extracted from PDF: {pdf_path}")
                return None
            
            full_text = '\n'.join(text_content)
            cleaned_text = self._clean_text(full_text)
            
            logger.info(f"Successfully extracted {len(cleaned_text)} characters from {pdf_path.name}")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text for better processing.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Basic text cleaning
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove leading/trailing whitespace
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Add line if it has content
            cleaned_lines.append(line)
        
        # Join lines with single newlines
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove excessive spaces within lines
        import re
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        
        return cleaned_text
    
    def get_pdf_metadata(self, pdf_path: Path) -> dict:
        """
        Extract metadata from PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            metadata = {}
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Basic file info
                metadata['file_name'] = pdf_path.name
                metadata['file_size'] = pdf_path.stat().st_size
                metadata['page_count'] = len(pdf_reader.pages)
                
                # PDF metadata
                if pdf_reader.metadata:
                    pdf_meta = pdf_reader.metadata
                    metadata['title'] = pdf_meta.get('/Title', '')
                    metadata['author'] = pdf_meta.get('/Author', '')
                    metadata['subject'] = pdf_meta.get('/Subject', '')
                    metadata['creator'] = pdf_meta.get('/Creator', '')
                    metadata['producer'] = pdf_meta.get('/Producer', '')
                    metadata['creation_date'] = str(pdf_meta.get('/CreationDate', ''))
                    metadata['modification_date'] = str(pdf_meta.get('/ModDate', ''))
                
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from PDF {pdf_path}: {e}")
            return {'error': str(e)}