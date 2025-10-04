"""
Document Processing Module for Legal Document Ingestion Workflow.

This module implements Step 1 of the three-step process:
- Extract and preprocess legal documents from PDF or JSON files
- Clean and chunk text as needed for inLegalBERT's 512-token limit
- Prepare documents with metadata for embedding generation
"""

import json
import re
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from dataclasses import dataclass
import PyPDF2
from datetime import datetime
import logging

from ..config.settings import get_settings

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Represents a processed document chunk with metadata."""
    text: str
    metadata: Dict[str, Any]
    chunk_id: int
    total_chunks: int
    source_file: str

class DocumentProcessor:
    """
    Processes legal documents from PDF and JSON formats.
    
    Handles:
    - PDF text extraction using PyPDF2
    - JSON parsing for structured legal data  
    - Text cleaning and preprocessing
    - Chunking for inLegalBERT's token limits
    - Metadata extraction and standardization
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.chunk_size = self.settings.processing.chunk_size
        self.chunk_overlap = self.settings.processing.chunk_overlap
        self.min_chunk_size = self.settings.processing.min_chunk_size
        
    def process_document(self, file_path: Union[str, Path], metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        Process a legal document file (PDF or JSON) into chunks.
        
        Args:
            file_path: Path to the document file
            metadata: Optional additional metadata to include
            
        Returns:
            List of DocumentChunk objects ready for embedding
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Determine file type and extract text
        if file_path.suffix.lower() in self.settings.processing.supported_pdf_extensions:
            text, extracted_metadata = self._extract_from_pdf(file_path)
        elif file_path.suffix.lower() in self.settings.processing.supported_json_extensions:
            text, extracted_metadata = self._extract_from_json(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        # Merge metadata
        final_metadata = self._prepare_metadata(file_path, extracted_metadata, metadata)
        
        # Clean and chunk text
        cleaned_text = self._clean_text(text)
        chunks = self._chunk_text(cleaned_text)
        
        # Create DocumentChunk objects
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk_metadata = final_metadata.copy()
            chunk_metadata.update({
                "chunk_id": i + 1,
                "total_chunks": len(chunks),
                "processing_timestamp": datetime.now().isoformat()
            })
            
            document_chunks.append(DocumentChunk(
                text=chunk_text,
                metadata=chunk_metadata,
                chunk_id=i + 1,
                total_chunks=len(chunks),
                source_file=str(file_path)
            ))
        
        logger.info(f"Processed {file_path.name}: {len(document_chunks)} chunks created")
        return document_chunks
    
    def _extract_from_pdf(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract text and metadata from PDF file."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += page_text + "\n\n"
                
                # Extract PDF metadata
                metadata = {}
                if pdf_reader.metadata:
                    metadata.update({
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "author": pdf_reader.metadata.get("/Author", ""),
                        "subject": pdf_reader.metadata.get("/Subject", ""),
                        "creator": pdf_reader.metadata.get("/Creator", ""),
                        "creation_date": str(pdf_reader.metadata.get("/CreationDate", "")),
                        "total_pages": len(pdf_reader.pages)
                    })
                
                return text.strip(), metadata
                
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from PDF {file_path}: {e}")
    
    def _extract_from_json(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract text and metadata from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Extract text from common JSON field names
            text_fields = ["content", "text", "body", "judgment", "decision", "full_text"]
            text = ""
            
            if isinstance(data, dict):
                # Try to find text in common fields
                for field in text_fields:
                    if field in data and isinstance(data[field], str):
                        text = data[field]
                        break
                
                # If no direct text field found, concatenate string values
                if not text:
                    text_parts = []
                    for key, value in data.items():
                        if isinstance(value, str) and len(value) > 50:  # Likely content, not metadata
                            text_parts.append(value)
                    text = "\n\n".join(text_parts)
                
                # Extract metadata (excluding the text field)
                metadata = {}
                for key, value in data.items():
                    if key not in text_fields and not isinstance(value, (list, dict)):
                        metadata[key] = str(value) if value is not None else ""
                
            elif isinstance(data, list):
                # Handle array of documents
                text_parts = []
                metadata = {"documents_count": len(data)}
                
                for item in data:
                    if isinstance(item, dict):
                        for field in text_fields:
                            if field in item and isinstance(item[field], str):
                                text_parts.append(item[field])
                                break
                
                text = "\n\n".join(text_parts)
            
            else:
                text = str(data)
                metadata = {}
            
            return text.strip(), metadata
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from JSON {file_path}: {e}")
    
    def _prepare_metadata(self, file_path: Path, extracted_metadata: Dict[str, Any], 
                         additional_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare and standardize metadata for the document."""
        metadata = {
            "source_file": file_path.name,
            "file_type": file_path.suffix.lower().replace(".", ""),
            "file_size": file_path.stat().st_size,
        }
        
        # Add extracted metadata
        metadata.update(extracted_metadata)
        
        # Add additional metadata if provided
        if additional_metadata:
            metadata.update(additional_metadata)
        
        # Set default values for standard legal document fields
        legal_fields = {
            "court": metadata.get("court", "Unknown"),
            "jurisdiction": metadata.get("jurisdiction", "Unknown"),
            "case_type": metadata.get("case_type", "Unknown"),
            "case_number": metadata.get("case_number", ""),
            "date": metadata.get("date", ""),
            "title": metadata.get("title", file_path.stem),
            "judges": metadata.get("judges", ""),
            "parties": metadata.get("parties", "")
        }
        
        metadata.update(legal_fields)
        
        # Clean metadata values
        for key, value in metadata.items():
            if isinstance(value, str):
                metadata[key] = value.strip()
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text for embedding generation."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep legal punctuation
        # Keep periods, commas, semicolons, colons, parentheses, quotes
        text = re.sub(r'[^\w\s\.\,\;\:\(\)\"\'\-\&\%\$\#]', ' ', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,;:])', r'\1', text)
        text = re.sub(r'([.,;:])\s+', r'\1 ', text)
        
        # Remove very long sequences of repeated characters
        text = re.sub(r'(.)\1{5,}', r'\1\1\1', text)
        
        # Remove extra spaces again
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into segments suitable for inLegalBERT's 512-token limit.
        
        Uses word-based chunking with overlap to maintain context.
        """
        if not text:
            return []
        
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            # Only add chunk if it meets minimum size requirement
            if len(chunk_words) >= self.min_chunk_size or start == 0:
                chunks.append(chunk_text)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= len(words):
                break
        
        return chunks
    
    def process_batch(self, file_paths: List[Union[str, Path]], 
                     metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[DocumentChunk]:
        """
        Process multiple documents in batch.
        
        Args:
            file_paths: List of file paths to process
            metadata_list: Optional list of metadata dicts (one per file)
            
        Returns:
            List of all DocumentChunk objects from all files
        """
        all_chunks = []
        
        for i, file_path in enumerate(file_paths):
            try:
                metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else None
                chunks = self.process_document(file_path, metadata)
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue
        
        logger.info(f"Batch processing completed: {len(all_chunks)} total chunks from {len(file_paths)} files")
        return all_chunks