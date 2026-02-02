"""
Cache Management Module for Legal Document Ingestion Workflow.

This module handles caching of processed files to prevent redundant reprocessing
and enable smart incremental ingestion while maintaining the existing architecture.
"""

import json
import logging
from pathlib import Path
from typing import Set, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class IngestionCacheManager:
    """
    Manages caching of processed files for incremental ingestion.
    
    Features:
    - Tracks successfully processed files
    - Prevents redundant reprocessing
    - Maintains processing metadata
    - Thread-safe file operations
    """
    
    def __init__(self, cache_file_path: Path = None):
        """
        Initialize the cache manager.
        
        Args:
            cache_file_path: Path to the cache file. Defaults to project root/cache.json
        """
        if cache_file_path is None:
            # Default to project root
            project_root = Path(__file__).parent.parent.parent
            cache_file_path = project_root / "cache.json"
        
        self.cache_file = cache_file_path
        self.cache_data = self._load_cache()
        
        logger.info(f"Cache manager initialized with cache file: {self.cache_file}")
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache data from file, creating default structure if not exists."""
        default_cache = {
            "processed_files": [],
            "processing_history": [],
            "last_updated": None,
            "total_files_processed": 0
        }
        
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # Ensure all required keys exist (backward compatibility)
                    for key in default_cache:
                        if key not in cache_data:
                            cache_data[key] = default_cache[key]
                    logger.info(f"Loaded cache with {len(cache_data.get('processed_files', []))} processed files")
                    return cache_data
            else:
                logger.info("No existing cache found, creating new cache")
                return default_cache
                
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache file: {e}. Creating new cache.")
            return default_cache
    
    def _save_cache(self):
        """Save cache data to file."""
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Update timestamp
            self.cache_data["last_updated"] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cache saved successfully to {self.cache_file}")
            
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")
            raise RuntimeError(f"Cache save failed: {e}")
    
    def is_file_processed(self, file_path: Path) -> bool:
        """
        Check if a file has already been processed.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file is in cache, False otherwise
        """
        file_name = file_path.name
        return file_name in self.cache_data.get("processed_files", [])
    
    def get_unprocessed_files(self, file_paths: List[Path]) -> List[Path]:
        """
        Filter out already processed files from a list.
        
        Args:
            file_paths: List of file paths to filter
            
        Returns:
            List of file paths that haven't been processed yet
        """
        unprocessed = []
        processed_files = set(self.cache_data.get("processed_files", []))
        
        for file_path in file_paths:
            if file_path.name not in processed_files:
                unprocessed.append(file_path)
            else:
                logger.info(f"Skipping already processed file: {file_path.name}")
        
        logger.info(f"Filtered {len(file_paths)} files -> {len(unprocessed)} unprocessed files")
        return unprocessed
    
    def mark_file_processed(self, file_path: Path, processing_info: Dict[str, Any] = None):
        """
        Mark a file as successfully processed.
        
        Args:
            file_path: Path to the processed file
            processing_info: Optional metadata about the processing
        """
        file_name = file_path.name
        
        # Add to processed files list if not already there
        if file_name not in self.cache_data["processed_files"]:
            self.cache_data["processed_files"].append(file_name)
            self.cache_data["total_files_processed"] = len(self.cache_data["processed_files"])
        
        # Add to processing history
        history_entry = {
            "file_name": file_name,
            "processed_at": datetime.now().isoformat(),
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
        }
        
        if processing_info:
            history_entry.update(processing_info)
        
        self.cache_data["processing_history"].append(history_entry)
        
        # Keep only last 100 history entries to prevent bloat
        if len(self.cache_data["processing_history"]) > 100:
            self.cache_data["processing_history"] = self.cache_data["processing_history"][-100:]
        
        # Save immediately to persist changes
        self._save_cache()
        
        logger.info(f"Marked file as processed: {file_name}")
    
    def mark_files_processed(self, file_paths: List[Path], processing_results: List[Dict[str, Any]] = None):
        """
        Mark multiple files as successfully processed.
        
        Args:
            file_paths: List of processed file paths
            processing_results: Optional list of processing metadata (same order as file_paths)
        """
        for i, file_path in enumerate(file_paths):
            processing_info = processing_results[i] if processing_results and i < len(processing_results) else None
            # Don't save after each file, batch the saves
            self._mark_file_processed_no_save(file_path, processing_info)
        
        # Save once after all files are marked
        self._save_cache()
        
        logger.info(f"Marked {len(file_paths)} files as processed")
    
    def _mark_file_processed_no_save(self, file_path: Path, processing_info: Dict[str, Any] = None):
        """Internal method to mark file processed without saving (for batch operations)."""
        file_name = file_path.name
        
        # Add to processed files list if not already there
        if file_name not in self.cache_data["processed_files"]:
            self.cache_data["processed_files"].append(file_name)
            self.cache_data["total_files_processed"] = len(self.cache_data["processed_files"])
        
        # Add to processing history
        history_entry = {
            "file_name": file_name,
            "processed_at": datetime.now().isoformat(),
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
        }
        
        if processing_info:
            history_entry.update(processing_info)
        
        self.cache_data["processing_history"].append(history_entry)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_processed_files": len(self.cache_data.get("processed_files", [])),
            "last_updated": self.cache_data.get("last_updated"),
            "cache_file_path": str(self.cache_file),
            "recent_files": self.cache_data.get("processed_files", [])[-10:],  # Last 10 files
            "cache_file_exists": self.cache_file.exists()
        }
    
    def clear_cache(self):
        """Clear all cache data (use with caution)."""
        self.cache_data = {
            "processed_files": [],
            "processing_history": [],
            "last_updated": None,
            "total_files_processed": 0
        }
        self._save_cache()
        logger.warning("Cache cleared - all files will be reprocessed on next run")
    
    def remove_file_from_cache(self, file_path: Path):
        """
        Remove a file from cache (forces reprocessing).
        
        Args:
            file_path: Path to the file to remove from cache
        """
        file_name = file_path.name
        
        if file_name in self.cache_data["processed_files"]:
            self.cache_data["processed_files"].remove(file_name)
            self.cache_data["total_files_processed"] = len(self.cache_data["processed_files"])
            self._save_cache()
            logger.info(f"Removed file from cache: {file_name}")
        else:
            logger.info(f"File not in cache: {file_name}")