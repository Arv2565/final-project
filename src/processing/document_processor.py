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

from config.settings import get_settings

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
        
        # Supported file extensions
        self.supported_extensions = (
            self.settings.processing.supported_pdf_extensions +
            self.settings.processing.supported_json_extensions +
            (".txt",)  # Add TXT support
        )
        
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
        elif file_path.suffix.lower() == ".txt":
            text, extracted_metadata = self._extract_from_txt(file_path)
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
            
            # Enhanced text extraction for legal documents
            text = ""
            metadata = {}
            
            if isinstance(data, list):
                # Handle array of legal documents (common structure)
                text_parts = []
                metadata = {"documents_count": len(data), "document_type": "legal_collection"}
                
                # Extract document type from filename for better categorization
                file_stem = file_path.stem.lower()
                metadata["collection_type"] = self._infer_collection_type(file_stem)
                
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        section_text = self._extract_text_from_legal_section(item, i + 1)
                        if section_text:
                            text_parts.append(section_text)
                
                text = "\n\n".join(text_parts)
                
            elif isinstance(data, dict):
                # Handle single document structure
                text = self._extract_text_from_legal_section(data, 1)
                metadata["document_type"] = "legal_document"
                
                # Extract metadata from the document
                for key, value in data.items():
                    if key not in ["section_desc", "description", "chapter,section,section_title,section_desc"] and not isinstance(value, (list, dict)):
                        metadata[key] = str(value) if value is not None else ""
            
            else:
                text = str(data)
                metadata = {"document_type": "unknown"}
            
            return text.strip(), metadata
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from JSON {file_path}: {e}")
    
    def _extract_from_txt(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract text and metadata from TXT file with legal document structure awareness."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Clean the content
            content = content.strip()
            
            # Extract basic metadata from the file structure
            metadata = self._extract_txt_metadata(file_path, content)
            
            return content, metadata
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from TXT {file_path}: {e}")
    
    def _extract_txt_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract metadata from TXT file based on content analysis."""
        metadata = {
            "document_type": "legal_text",
            "content_length": len(content),
            "estimated_sections": 0
        }
        
        filename_lower = file_path.stem.lower()
        
        # Analyze content for legal document patterns
        lines = content.split('\n')
        section_patterns = [
            r'\[s\s*\d+\]',  # [s 1], [s 2], etc.
            r'section\s+\d+',  # Section 1, Section 2, etc.
            r'article\s+\d+',  # Article 1, Article 2, etc.
            r'chapter\s+[ivxlc\d]+',  # Chapter I, Chapter 1, etc.
        ]
        
        section_count = 0
        for line in lines:
            for pattern in section_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    section_count += 1
                    break
        
        metadata["estimated_sections"] = section_count
        
        # Infer document type from filename and content
        if "ipc" in filename_lower or "penal" in content.lower():
            metadata["legal_domain"] = "criminal_law"
            metadata["document_title"] = "Indian Penal Code"
            metadata["act_type"] = "penal_code"
        elif "constitution" in filename_lower or "constitutional" in content.lower():
            metadata["legal_domain"] = "constitutional_law"
            metadata["document_title"] = "Constitution of India"
            metadata["act_type"] = "constitution"
        else:
            metadata["legal_domain"] = "general_law"
            metadata["document_title"] = file_path.stem.replace('_', ' ').title()
            metadata["act_type"] = "legal_text"
        
        return metadata
    
    def _prepare_metadata(self, file_path: Path, extracted_metadata: Dict[str, Any],
                         additional_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare and standardize metadata for the document with legal domain context."""
        metadata = {
            "source": file_path.name,  # Following the requirement for 'source' tag
            "source_file": file_path.name,
            "file_type": file_path.suffix.lower().replace(".", ""),
            "file_size": file_path.stat().st_size,
        }
        
        # Add extracted metadata
        metadata.update(extracted_metadata)
        
        # Add additional metadata if provided
        if additional_metadata:
            metadata.update(additional_metadata)
        
        # Infer and add legal document source type for better GraphRAG context
        source_type = self._detect_legal_document_source(file_path, extracted_metadata)
        metadata["legal_document_source"] = source_type
        
        # Enhanced category inference for legal documents
        if file_path.suffix.lower() == ".json":
            categories = self._infer_legal_categories(file_path, extracted_metadata)
            metadata["category"] = categories["primary"]
            metadata["subcategory"] = categories["secondary"]
            # Add multiple category tags as required
            for i, tag in enumerate(categories["tags"]):
                metadata[f"tag_{i+1}"] = tag
        elif file_path.suffix.lower() == ".txt":
            categories = self._infer_txt_categories(file_path, extracted_metadata)
            metadata["category"] = categories["primary"]
            metadata["subcategory"] = categories["secondary"]
            # Add multiple category tags as required
            for i, tag in enumerate(categories["tags"]):
                metadata[f"tag_{i+1}"] = tag
        elif file_path.suffix.lower() == ".pdf":
            categories = self._infer_pdf_categories(file_path, extracted_metadata)
            metadata["category"] = categories["primary"]
            metadata["subcategory"] = categories["secondary"]
            # Add multiple category tags as required
            for i, tag in enumerate(categories["tags"]):
                metadata[f"tag_{i+1}"] = tag
        
        # Set default values for standard legal document fields
        legal_fields = {
            "court": metadata.get("court", "Unknown"),
            "jurisdiction": metadata.get("jurisdiction", "India"),  # Default to India for legal docs
            "case_type": metadata.get("case_type", metadata.get("collection_type", "Unknown")),
            "case_number": metadata.get("case_number", ""),
            "date": metadata.get("date", ""),
            "title": metadata.get("title", file_path.stem),
            "judges": metadata.get("judges", ""),
            "parties": metadata.get("parties", ""),
            "document_class": "legal_statute"  # Default for JSON legal documents
        }
        
        metadata.update(legal_fields)
        
        # Clean metadata values
        for key, value in metadata.items():
            if isinstance(value, str):
                metadata[key] = value.strip()
        
        return metadata
    
    def _detect_legal_document_source(self, file_path: Path, extracted_metadata: Dict[str, Any]) -> str:
        """
        Detect the legal document source type (IPC, Constitution, CPC, etc.)
        for GraphRAG context awareness.
        
        Returns a source type string like 'ipc', 'constitution', 'cpc', etc.
        """
        filename_lower = file_path.stem.lower()
        content_sample = extracted_metadata.get("title", "").lower() + " " + extracted_metadata.get("subject", "").lower()
        
        # Check IPC (Indian Penal Code)
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["ipc", "penal_code", "penal code"]):
            return "ipc"
        
        # Check Constitution
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["constitution", "constitutional", "const"]):
            return "constitution"
        
        # Check CPC (Code of Civil Procedure)
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["cpc", "civil_procedure", "civil procedure"]):
            return "cpc"
        
        # Check CrPC (Code of Criminal Procedure)
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["crpc", "criminal_procedure", "criminal procedure"]):
            return "crpc"
        
        # Check Indian Evidence Act
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["iea", "evidence_act", "evidence act"]):
            return "iea"
        
        # Check Hindu Marriage Act
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["hma", "marriage_act", "marriage act"]):
            return "hma"
        
        # Check Motor Vehicle Act
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["mva", "motor_vehicle", "motor vehicle"]):
            return "mva"
        
        # Check Negotiable Instruments Act
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["nia", "negotiable_instruments", "negotiable instruments"]):
            return "nia"
        
        # Check Indian Divorce Act
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["ida", "divorce_act", "divorce act"]):
            return "ida"
        
        # Check Kerala Acts
        if any(keyword in filename_lower or keyword in content_sample for keyword in ["kerala", "kerala_acts"]):
            return "kerala_acts"
        
        # Default generic legal document
        return "legal_document"
    
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
    
    def _extract_text_from_legal_section(self, item: Dict[str, Any], section_number: int) -> str:
        """Extract text content from a legal document section."""
        text_parts = []
        
        # Handle different JSON structures for legal documents
        if "section_desc" in item and item["section_desc"]:
            # Structure: {"section": X, "section_title": Y, "section_desc": Z}
            section = item.get("section", section_number)
            title = item.get("section_title", "")
            desc = item["section_desc"]
            chapter = item.get("chapter", "")
            
            if chapter:
                text_parts.append(f"Chapter {chapter}")
            if section:
                text_parts.append(f"Section {section}")
            if title:
                text_parts.append(f"Title: {title}")
            text_parts.append(desc)
            
        elif "description" in item and item["description"]:
            # Structure: {"section": X, "title": Y, "description": Z}
            section = item.get("section", section_number)
            title = item.get("title", "")
            desc = item["description"]
            
            if section:
                text_parts.append(f"Section {section}")
            if title:
                text_parts.append(f"Title: {title}")
            text_parts.append(desc)
            
        elif "chapter,section,section_title,section_desc" in item:
            # Structure: {"chapter,section,section_title,section_desc": "1,2,Title,Description"}
            combined_data = item["chapter,section,section_title,section_desc"]
            if combined_data and combined_data.strip():
                parts = combined_data.split(",", 3)  # Split into max 4 parts
                if len(parts) >= 4:
                    chapter, section, title, desc = parts
                    if chapter:
                        text_parts.append(f"Chapter {chapter}")
                    if section:
                        text_parts.append(f"Section {section}")
                    if title:
                        text_parts.append(f"Title: {title}")
                    if desc:
                        text_parts.append(desc)
        
        else:
            # Fallback: look for any text fields
            text_fields = ["content", "text", "body", "judgment", "decision", "full_text"]
            for field in text_fields:
                if field in item and isinstance(item[field], str) and item[field].strip():
                    text_parts.append(item[field])
                    break
            
            # If still no text, concatenate all string values longer than 50 chars
            if not text_parts:
                for key, value in item.items():
                    if isinstance(value, str) and len(value) > 50:
                        text_parts.append(f"{key}: {value}")
        
        return "\n".join(text_parts)
    
    def _infer_collection_type(self, filename_stem: str) -> str:
        """Infer the legal collection type from filename."""
        type_mapping = {
            "crpc": "criminal_procedure",
            "crp": "criminal_procedure", 
            "cpc": "civil_procedure",
            "cpa": "civil_procedure",
            "mva": "motor_vehicle",
            "mvа": "motor_vehicle",  # Handle potential unicode issues
            "hma": "hindu_marriage",
            "ida": "indian_divorce",
            "iea": "indian_evidence",
            "nia": "negotiable_instruments",
            "ipc": "indian_penal_code",
            "contract": "contract_law",
            "property": "property_law",
            "company": "company_law",
            "constitution": "constitutional_law"
        }
        
        # Try exact match first
        if filename_stem in type_mapping:
            return type_mapping[filename_stem]
        
        # Try partial matches
        for key, value in type_mapping.items():
            if key in filename_stem or filename_stem in key:
                return value
        
        # Default classification
        return "legal_document"
    
    def _infer_legal_categories(self, file_path: Path, extracted_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Infer detailed legal categories from filename and content."""
        filename_stem = file_path.stem.lower()
        collection_type = extracted_metadata.get("collection_type", "legal_document")
        
        # Define category mappings with primary, secondary categories and tags
        category_mappings = {
            "criminal_procedure": {
                "primary": "legal",
                "secondary": "criminal_law",
                "tags": ["criminal_procedure", "crpc", "legal", "procedure", "courts"]
            },
            "civil_procedure": {
                "primary": "legal",
                "secondary": "civil_law",
                "tags": ["civil_procedure", "cpc", "legal", "procedure", "courts"]
            },
            "motor_vehicle": {
                "primary": "legal",
                "secondary": "transport_law",
                "tags": ["motor_vehicle", "transport", "traffic", "legal", "mva"]
            },
            "hindu_marriage": {
                "primary": "legal",
                "secondary": "family_law",
                "tags": ["marriage", "hindu_law", "family", "legal", "personal_law"]
            },
            "indian_divorce": {
                "primary": "legal",
                "secondary": "family_law",
                "tags": ["divorce", "family", "legal", "personal_law"]
            },
            "indian_evidence": {
                "primary": "legal",
                "secondary": "evidence_law",
                "tags": ["evidence", "procedure", "legal", "courts"]
            },
            "negotiable_instruments": {
                "primary": "legal",
                "secondary": "commercial_law",
                "tags": ["negotiable_instruments", "banking", "commercial", "legal"]
            },
            "indian_penal_code": {
                "primary": "legal",
                "secondary": "criminal_law",
                "tags": ["penal_code", "criminal", "offences", "legal"]
            }
        }
        
        # Get category info based on collection type
        category_info = category_mappings.get(collection_type, {
            "primary": "legal",
            "secondary": "general_law",
            "tags": ["legal", "statute"]
        })
        
        # Add source-specific tags
        source_tags = [filename_stem, "indian_law", "statute"]
        all_tags = category_info["tags"] + source_tags
        
        # Remove duplicates while preserving order
        unique_tags = []
        for tag in all_tags:
            if tag not in unique_tags:
                unique_tags.append(tag)
        
        return {
            "primary": category_info["primary"],
            "secondary": category_info["secondary"],
            "tags": unique_tags[:10]  # Limit to 10 tags to avoid clutter
        }
    
    def _infer_txt_categories(self, file_path: Path, extracted_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Infer detailed legal categories for TXT files."""
        filename_stem = file_path.stem.lower()
        legal_domain = extracted_metadata.get("legal_domain", "general_law")
        
        # Category mappings for different legal domains
        if legal_domain == "criminal_law" or "ipc" in filename_stem:
            return {
                "primary": "legal",
                "secondary": "criminal_law",
                "tags": ["indian_penal_code", "ipc", "criminal", "offences", "legal", "punishment", "crimes"]
            }
        elif legal_domain == "constitutional_law" or "constitution" in filename_stem:
            return {
                "primary": "legal",
                "secondary": "constitutional_law",
                "tags": ["constitution", "fundamental_rights", "constitutional", "legal", "governance", "articles"]
            }
        else:
            return {
                "primary": "legal",
                "secondary": "general_law",
                "tags": ["legal", "statute", "text", "indian_law"]
            }
    
    def _infer_pdf_categories(self, file_path: Path, extracted_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Infer detailed legal categories for PDF files."""
        filename_stem = file_path.stem.lower()
        title = extracted_metadata.get("title", "").lower()
        
        # Infer from filename and title
        if "constitution" in filename_stem or "constitution" in title:
            return {
                "primary": "legal",
                "secondary": "constitutional_law",
                "tags": ["constitution", "fundamental_rights", "constitutional", "legal", "governance", "articles", "pdf"]
            }
        elif "penal" in filename_stem or "penal" in title or "ipc" in filename_stem:
            return {
                "primary": "legal",
                "secondary": "criminal_law",
                "tags": ["penal_code", "criminal", "offences", "legal", "pdf"]
            }
        elif "civil" in filename_stem or "civil" in title:
            return {
                "primary": "legal",
                "secondary": "civil_law",
                "tags": ["civil", "procedure", "legal", "pdf"]
            }
        else:
            return {
                "primary": "legal",
                "secondary": "general_law",
                "tags": ["legal", "document", "pdf", "indian_law"]
            }
    
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