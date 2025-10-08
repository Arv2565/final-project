"""
inLegalBERT Embedding Service Module for Legal Document Ingestion Workflow.

This module implements Step 2 of the three-step process:
- Generate dense embeddings using the inLegalBERT model
- Handle batching and device management
- Respect the 512-token limit of the model
- Process document chunks efficiently
"""

import torch
import numpy as np
from typing import List, Optional, Union, Any
from transformers import AutoTokenizer, AutoModel
import logging
from dataclasses import dataclass

from config.settings import get_settings
from processing.document_processor import DocumentChunk

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embeddings: np.ndarray
    chunk_count: int
    model_used: str
    device_used: str

class InLegalBERTEmbeddingService:
    """
    Embedding service using inLegalBERT (nlpaueb/legal-bert-base-uncased).
    
    This service:
    - Loads the inLegalBERT model and tokenizer
    - Generates 768-dimensional embeddings
    - Handles batching for efficiency
    - Manages device placement (CPU/GPU)
    - Respects the 512-token limit
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.model_name = self.settings.embedding.model_name
        self.max_length = self.settings.embedding.max_token_length
        self.batch_size = self.settings.embedding.batch_size
        self.device = self._setup_device()
        
        # Initialize model and tokenizer
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _setup_device(self) -> str:
        """Setup and return the device to use for inference."""
        device_setting = self.settings.embedding.device
        
        if device_setting == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"  # Apple Silicon GPU
            else:
                device = "cpu"
        else:
            device = device_setting
        
        logger.info(f"Using device: {device}")
        return device
    
    def _load_model(self):
        """Load the inLegalBERT model and tokenizer."""
        try:
            logger.info(f"Loading inLegalBERT model: {self.model_name}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                do_lower_case=True
            )
            
            # Load model
            self.model = AutoModel.from_pretrained(
                self.model_name,
                output_hidden_states=False,
                output_attentions=False
            )
            
            # Move model to device
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            logger.info(f"Successfully loaded inLegalBERT model on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load inLegalBERT model: {e}")
            raise RuntimeError(f"Could not load embedding model: {e}")
    
    def generate_embeddings(self, texts: List[str]) -> EmbeddingResult:
        """
        Generate embeddings for a list of text chunks.
        
        Args:
            texts: List of text chunks to embed
            
        Returns:
            EmbeddingResult containing the embeddings and metadata
        """
        if not texts:
            return EmbeddingResult(
                embeddings=np.array([]),
                chunk_count=0,
                model_used=self.model_name,
                device_used=self.device
            )
        
        logger.info(f"Generating embeddings for {len(texts)} text chunks")
        
        embeddings = []
        
        # Process texts in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = self._embed_batch(batch_texts)
            embeddings.extend(batch_embeddings)
        
        embeddings_array = np.array(embeddings)
        
        logger.info(f"Generated embeddings shape: {embeddings_array.shape}")
        
        return EmbeddingResult(
            embeddings=embeddings_array,
            chunk_count=len(texts),
            model_used=self.model_name,
            device_used=self.device
        )
    
    def _embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: Batch of texts to embed
            
        Returns:
            List of embedding arrays
        """
        try:
            # Tokenize texts
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt"
            )
            
            # Move tensors to device
            input_ids = encoded['input_ids'].to(self.device)
            attention_mask = encoded['attention_mask'].to(self.device)
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                
                # Use CLS token embeddings (first token)
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            return [emb for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Error generating embeddings for batch: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def embed_document_chunks(self, chunks: List[DocumentChunk]) -> List[tuple[DocumentChunk, np.ndarray]]:
        """
        Generate embeddings for a list of DocumentChunk objects.
        
        Args:
            chunks: List of DocumentChunk objects
            
        Returns:
            List of tuples (chunk, embedding_array)
        """
        if not chunks:
            return []
        
        texts = [chunk.text for chunk in chunks]
        embedding_result = self.generate_embeddings(texts)
        
        # Pair chunks with their embeddings
        chunk_embedding_pairs = []
        for chunk, embedding in zip(chunks, embedding_result.embeddings):
            chunk_embedding_pairs.append((chunk, embedding))
        
        return chunk_embedding_pairs
    
    def embed_single_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding array
        """
        if not text:
            return np.zeros(768)  # Return zero vector for empty text
        
        result = self.generate_embeddings([text])
        return result.embeddings[0] if len(result.embeddings) > 0 else np.zeros(768)
    
    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension (768 for inLegalBERT)."""
        return 768
    
    def validate_token_length(self, text: str) -> bool:
        """
        Check if text is within token limits.
        
        Args:
            text: Text to validate
            
        Returns:
            True if text is within limits, False otherwise
        """
        if not self.tokenizer:
            return True  # Can't validate without tokenizer
        
        tokens = self.tokenizer.encode(text, add_special_tokens=True)
        return len(tokens) <= self.max_length
    
    def get_token_count(self, text: str) -> int:
        """
        Get the token count for a text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not self.tokenizer:
            return 0
        
        tokens = self.tokenizer.encode(text, add_special_tokens=True)
        return len(tokens)
    
    def cleanup(self):
        """Clean up resources."""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Embedding service resources cleaned up")

# Singleton instance for global use
_embedding_service: Optional[InLegalBERTEmbeddingService] = None

def get_embedding_service() -> InLegalBERTEmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = InLegalBERTEmbeddingService()
    return _embedding_service

def cleanup_embedding_service():
    """Clean up the global embedding service."""
    global _embedding_service
    if _embedding_service:
        _embedding_service.cleanup()
        _embedding_service = None