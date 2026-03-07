"""
Case JSON Loader Service for Retrieving Full Case Data.

Loads complete case JSON from casefiles.json indexed by citation.
Implements caching for performance optimization.
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)


class CaseJSONLoader:
    """Loads and caches full case JSON data by citation."""
    
    def __init__(self, casefiles_path: str = "tool/data/casefiles.json"):
        """
        Initialize the case JSON loader.
        
        Args:
            casefiles_path: Path to casefiles.json relative to workspace root
        """
        self.casefiles_path = casefiles_path
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._loaded = False
        logger.info(f"CaseJSONLoader initialized with path: {casefiles_path}")
    
    def load_case_by_citation(self, citation: str) -> Optional[Dict[str, Any]]:
        """
        Load complete case JSON by citation.
        
        Args:
            citation: Citation string to look up (e.g., "[2021] 3 S.C.R. 576")
        
        Returns:
            Complete case JSON dict if found, None otherwise
        
        Raises:
            FileNotFoundError: If casefiles.json doesn't exist
            json.JSONDecodeError: If casefiles.json is invalid
        """
        try:
            # Load cache if not already loaded
            if not self._loaded:
                self._load_cache()
            
            # Look up case in cache
            case = self._cache.get(citation)
            
            if case:
                logger.debug(f"Retrieved case from cache: {citation}")
                return case
            else:
                logger.warning(f"Case not found in cache: {citation}")
                return None
        
        except Exception as e:
            logger.error(f"Error loading case by citation {citation}: {e}")
            raise
    
    def load_all_cases(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all cases from casefiles.json.
        
        Returns:
            Dict mapping citation -> case data
        """
        if not self._loaded:
            self._load_cache()
        return self._cache.copy()
    
    def _load_cache(self):
        """Load all cases from casefiles.json into memory cache."""
        try:
            # Resolve path: start from current directory
            if not os.path.isabs(self.casefiles_path):
                # Try from current working directory first
                if not os.path.exists(self.casefiles_path):
                    # Try from workspace root
                    workspace_root = self._find_workspace_root()
                    self.casefiles_path = os.path.join(workspace_root, self.casefiles_path)
            
            if not os.path.exists(self.casefiles_path):
                raise FileNotFoundError(f"casefiles.json not found at {self.casefiles_path}")
            
            logger.info(f"Loading casefiles from {self.casefiles_path}")
            
            with open(self.casefiles_path, 'r', encoding='utf-8') as f:
                cases = json.load(f)
            
            if not isinstance(cases, list):
                raise ValueError("casefiles.json root must be an array")
            
            # Build citation -> case mapping
            for case in cases:
                citation = case.get("metadata", {}).get("citation")
                if citation:
                    self._cache[citation] = case
                else:
                    logger.warning(f"Case without citation found, skipping: {case.get('case_id', 'Unknown')}")
            
            self._loaded = True
            logger.info(f"Loaded {len(self._cache)} cases into cache from casefiles.json")
        
        except Exception as e:
            logger.error(f"Error loading casefiles.json: {e}")
            raise
    
    def _find_workspace_root(self) -> str:
        """Find workspace root by looking for typical markers."""
        current = os.getcwd()
        
        for _ in range(5):  # Search up to 5 levels
            if os.path.exists(os.path.join(current, "tool")):
                return current
            if os.path.exists(os.path.join(current, "pyproject.toml")):
                return current
            current = os.path.dirname(current)
        
        return os.getcwd()
    
    def clear_cache(self):
        """Clear in-memory cache."""
        self._cache.clear()
        self._loaded = False
        logger.info("Case JSON cache cleared")
    
    def get_cache_size(self) -> int:
        """Get number of cases in cache."""
        if not self._loaded:
            self._load_cache()
        return len(self._cache)


# Singleton instance for application-wide reuse
_loader_instance: Optional[CaseJSONLoader] = None


def get_case_json_loader() -> CaseJSONLoader:
    """Get or create singleton case JSON loader instance."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = CaseJSONLoader()
    return _loader_instance
