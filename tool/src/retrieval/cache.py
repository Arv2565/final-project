"""
Query result caching for retrieval operations.

Implements in-memory and optional persistent caching of retrieval results
to reduce redundant queries to Qdrant and Neo4j.
"""

import logging
import time
import hashlib
from typing import Dict, Any, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)


class RetrievalCache:
    """
    Simple in-memory cache for retrieval results.
    
    Uses query text hashing to avoid storing query strings directly.
    Supports TTL (time-to-live) for cache entries.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of cached queries
            ttl_seconds: Time-to-live for cached entries (seconds)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def _hash_query(query: str) -> str:
        """Create hash of query for cache key."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]
    
    def get(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached results for query.
        
        Args:
            query: Query text
            
        Returns:
            Cached results if available and not expired, None otherwise
        """
        key = self._hash_query(query)
        
        if key not in self._cache:
            return None
        
        cached = self._cache[key]
        
        # Check TTL
        if time.time() - cached["timestamp"] > self.ttl_seconds:
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit for query (hash: {key})")
        return cached["results"]
    
    def set(self, query: str, results: List[Dict[str, Any]]) -> None:
        """
        Cache results for a query.
        
        Args:
            query: Query text
            results: Results to cache
        """
        key = self._hash_query(query)
        
        # Simple eviction: if cache full, remove oldest entry
        if len(self._cache) >= self.max_size:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            del self._cache[oldest_key]
            logger.debug(f"Cache evicted oldest entry (hash: {oldest_key})")
        
        self._cache[key] = {
            "results": results,
            "timestamp": time.time()
        }
        logger.debug(f"Cached results for query (hash: {key})")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


# Global cache instance
_retrieval_cache = RetrievalCache()


def get_retrieval_cache() -> RetrievalCache:
    """Get the global retrieval cache instance."""
    return _retrieval_cache


def cache_retrieval_result(
    query: str,
    results: List[Dict[str, Any]],
    use_cache: bool = True
) -> None:
    """
    Cache retrieval results.
    
    Args:
        query: Query text
        results: Results to cache
        use_cache: Whether caching is enabled
    """
    if use_cache:
        _retrieval_cache.set(query, results)


def get_cached_result(
    query: str,
    use_cache: bool = True
) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached results for query if available.
    
    Args:
        query: Query text
        use_cache: Whether caching is enabled
        
    Returns:
        Cached results or None if not found/disabled
    """
    if use_cache:
        return _retrieval_cache.get(query)
    return None
