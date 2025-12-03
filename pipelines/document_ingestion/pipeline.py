"""
Legal Document Ingestion Workflow Orchestrator.

This module orchestrates the complete three-step process:
1. Extract and preprocess legal documents (PDF/JSON)
2. Generate embeddings using inLegalBERT
3. Store embeddings with metadata in Qdrant

The workflow is designed for clarity, modularity, and scalability
while preserving the core functionality of each step.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipelines.document_ingestion.processor import DocumentProcessor, DocumentChunk
from src.database.embeddings import get_embedding_service, cleanup_embedding_service
from src.database.qdrant.client import get_qdrant_store, cleanup_qdrant_store
from src.config import get_settings, validate_environment

logger = logging.getLogger(__name__)

@dataclass
class IngestionResult:
    """Result of the document ingestion workflow."""
    total_files: int
    successful_files: int
    failed_files: int
    total_chunks: int
    stored_points: List[str]
    processing_time: float
    errors: List[Dict[str, Any]]

@dataclass
class FileProcessingResult:
    """Result of processing a single file."""
    file_path: str
    success: bool
    chunks_created: int
    points_stored: List[str]
    error: Optional[str] = None

class LegalDocumentIngestionWorkflow:
    """
    Orchestrates the three-step legal document ingestion process.
    
    This workflow:
    1. Processes documents (PDF/JSON) into chunks with metadata
    2. Generates inLegalBERT embeddings for text chunks
    3. Stores embeddings and metadata in Qdrant collection
    
    Designed for production use with error handling, logging, and scalability.
    """
    
    def __init__(self):
        """Initialize the workflow with all required services."""
        # Validate environment first
        if not validate_environment():
            raise RuntimeError("Environment validation failed. Check configuration.")
        
        self.settings = get_settings()
        
        # Initialize services
        self.document_processor = DocumentProcessor()
        self.embedding_service = get_embedding_service()
        self.qdrant_store = get_qdrant_store()
        
        logger.info("Legal Document Ingestion Workflow initialized")
        logger.info(f"Configuration: {self.settings.qdrant.collection_name} collection, {self.settings.embedding.model_name} embeddings")
    
    def ingest_documents(self, 
                        file_paths: List[Union[str, Path]], 
                        metadata_list: Optional[List[Dict[str, Any]]] = None,
                        batch_size: Optional[int] = None) -> IngestionResult:
        """
        Ingest multiple legal documents through the complete three-step workflow.
        
        Args:
            file_paths: List of file paths to process (PDF or JSON)
            metadata_list: Optional list of metadata dicts (one per file)
            batch_size: Optional batch size for processing (uses config default if None)
            
        Returns:
            IngestionResult containing processing statistics and results
        """
        start_time = time.time()
        
        logger.info(f"Starting ingestion workflow for {len(file_paths)} files")
        
        # Initialize result tracking
        result = IngestionResult(
            total_files=len(file_paths),
            successful_files=0,
            failed_files=0,
            total_chunks=0,
            stored_points=[],
            processing_time=0.0,
            errors=[]
        )
        
        # Process files individually to handle errors gracefully
        for i, file_path in enumerate(file_paths):
            try:
                metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else None
                file_result = self.ingest_single_document(file_path, metadata)
                
                if file_result.success:
                    result.successful_files += 1
                    result.total_chunks += file_result.chunks_created
                    result.stored_points.extend(file_result.points_stored)
                else:
                    result.failed_files += 1
                    if file_result.error:
                        result.errors.append({
                            "file": str(file_path),
                            "error": file_result.error
                        })
                
            except Exception as e:
                logger.error(f"Unexpected error processing {file_path}: {e}")
                result.failed_files += 1
                result.errors.append({
                    "file": str(file_path),
                    "error": f"Unexpected error: {str(e)}"
                })
        
        result.processing_time = time.time() - start_time
        
        # Log final results
        logger.info(f"Ingestion workflow completed in {result.processing_time:.2f} seconds")
        logger.info(f"Success: {result.successful_files}/{result.total_files} files")
        logger.info(f"Total chunks processed: {result.total_chunks}")
        logger.info(f"Total points stored: {len(result.stored_points)}")
        
        if result.errors:
            logger.warning(f"Encountered {len(result.errors)} errors during processing")
        
        return result
    
    def ingest_single_document(self, 
                              file_path: Union[str, Path], 
                              metadata: Optional[Dict[str, Any]] = None) -> FileProcessingResult:
        """
        Ingest a single document through the complete three-step workflow.
        
        Args:
            file_path: Path to the document file
            metadata: Optional metadata to include
            
        Returns:
            FileProcessingResult for this specific file
        """
        file_path = Path(file_path)
        logger.info(f"Processing document: {file_path.name}")
        
        try:
            # Step 1: Extract and preprocess document
            logger.debug(f"Step 1: Processing document {file_path.name}")
            chunks = self.document_processor.process_document(file_path, metadata)
            
            if not chunks:
                return FileProcessingResult(
                    file_path=str(file_path),
                    success=False,
                    chunks_created=0,
                    points_stored=[],
                    error="No chunks were created from the document"
                )
            
            # Step 2: Generate embeddings
            logger.debug(f"Step 2: Generating embeddings for {len(chunks)} chunks")
            chunk_embedding_pairs = self.embedding_service.embed_document_chunks(chunks)
            
            if not chunk_embedding_pairs:
                return FileProcessingResult(
                    file_path=str(file_path),
                    success=False,
                    chunks_created=len(chunks),
                    points_stored=[],
                    error="Failed to generate embeddings"
                )
            
            # Step 3: Store in Qdrant
            logger.debug(f"Step 3: Storing {len(chunk_embedding_pairs)} embeddings in Qdrant")
            point_ids = self.qdrant_store.store_document_chunks(chunk_embedding_pairs)
            
            logger.info(f"Successfully processed {file_path.name}: {len(chunks)} chunks, {len(point_ids)} points stored")
            
            return FileProcessingResult(
                file_path=str(file_path),
                success=True,
                chunks_created=len(chunks),
                points_stored=point_ids
            )
            
        except Exception as e:
            error_msg = f"Error processing {file_path.name}: {str(e)}"
            logger.error(error_msg)
            
            return FileProcessingResult(
                file_path=str(file_path),
                success=False,
                chunks_created=0,
                points_stored=[],
                error=error_msg
            )
    
    def ingest_directory(self, 
                        directory_path: Union[str, Path], 
                        recursive: bool = True,
                        file_pattern: str = "*",
                        metadata_extractor: Optional[callable] = None) -> IngestionResult:
        """
        Ingest all legal documents from a directory.
        
        Args:
            directory_path: Path to directory containing documents
            recursive: Whether to search subdirectories
            file_pattern: File pattern to match (e.g., "*.pdf", "*.json")
            metadata_extractor: Optional function to extract metadata from file paths
            
        Returns:
            IngestionResult containing processing statistics
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        # Find all matching files
        if recursive:
            files = list(directory_path.rglob(file_pattern))
        else:
            files = list(directory_path.glob(file_pattern))
        
        # Filter for supported file types
        supported_extensions = (
            self.settings.processing.supported_pdf_extensions + 
            self.settings.processing.supported_json_extensions
        )
        
        files = [f for f in files if f.suffix.lower() in supported_extensions]
        
        logger.info(f"Found {len(files)} legal documents in {directory_path}")
        
        # Extract metadata if extractor provided
        metadata_list = None
        if metadata_extractor:
            try:
                metadata_list = [metadata_extractor(f) for f in files]
            except Exception as e:
                logger.warning(f"Metadata extraction failed: {e}")
                metadata_list = None
        
        return self.ingest_documents(files, metadata_list)
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get the current status of the Qdrant collection."""
        try:
            stats = self.qdrant_store.get_collection_stats()
            return {
                "status": "healthy",
                "collection_stats": stats,
                "embedding_model": self.settings.embedding.model_name,
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    def search_similar_documents(self, 
                                query_text: str,
                                limit: int = 10,
                                score_threshold: float = 0.0,
                                filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query text.
        
        Args:
            query_text: Text to search for
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Optional filters (e.g., {"court": "Supreme Court"})
            
        Returns:
            List of similar document chunks with scores and metadata
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.embed_single_text(query_text)
            
            # Search in Qdrant
            results = self.qdrant_store.search_similar_chunks(
                query_embedding=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                filters=filters
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Document search failed: {e}")
    
    def cleanup(self):
        """Clean up all resources and connections."""
        try:
            cleanup_embedding_service()
            cleanup_qdrant_store()
            logger.info("Workflow cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Global workflow instance
_workflow: Optional[LegalDocumentIngestionWorkflow] = None

def get_ingestion_workflow() -> LegalDocumentIngestionWorkflow:
    """Get the global ingestion workflow instance."""
    global _workflow
    if _workflow is None:
        _workflow = LegalDocumentIngestionWorkflow()
    return _workflow

def cleanup_workflow():
    """Clean up the global workflow instance."""
    global _workflow
    if _workflow:
        _workflow.cleanup()
        _workflow = None