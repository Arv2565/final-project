"""Combined graph + vector retrieval helpers.

Provides efficient retrieval combining:
1. Native Neo4j vector index search (when available) for scalable ANN queries
2. Fallback to Python cosine similarity for environments without vector indexes
3. Graph-based expansion for semantic traversal

This implementation uses Neo4j 5.0+ native vector indexes when available,
providing O(log n) query time vs O(n) with Python cosine. Gracefully degrades
to Python-side computation for older Neo4j versions or when index unavailable.

Performance characteristics:
- Native search: O(log n) index lookup, returns only top-k results
- Python fallback: O(n) similarity computation, requires in-memory processing
- Recommended: Use native search for graphs with 1000+ entities
"""
from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any, Optional

from src.database.neo4j.client import neo4j_session
from src.utils.vector_retrieval import (
    vector_search,
    vector_search_native,
    vector_search_python,
    SimilarityFunction,
    get_vector_search_stats,
)

logger = logging.getLogger(__name__)


def vector_nearest_entities(
    query: str,
    top_k: int = 10,
    entity_type_filter: Optional[str] = None,
) -> List[Tuple[str, float, Dict[str, Any]]]:
    """Return top_k entities matching query with similarity scores and metadata.

    This is the primary vector search interface. It automatically:
    1. Detects Neo4j vector index availability
    2. Uses native ANN search if available (O(log n))
    3. Falls back to Python cosine if needed (O(n))
    
    Args:
        query: Query text to search for
        top_k: Number of top results to return
        entity_type_filter: Optional filter for entity type (e.g., 'Section', 'Act')
        
    Returns:
        List of (entity_name, similarity_score, metadata) tuples sorted by score descending
        
    Example:
        >>> results = vector_nearest_entities(
        ...     query="Section 420 cheating IPC",
        ...     top_k=10,
        ...     entity_type_filter="Section"
        ... )
    """
    try:
        # Build filters dict
        filters = None
        if entity_type_filter:
            filters = {"entity_type": entity_type_filter}
        
        # Use optimized vector search
        results = vector_search(
            query=query,
            top_k=top_k,
            similarity_function=SimilarityFunction.COSINE,
            where_filters=filters,
        )
        
        logger.info(f"Vector search returned {len(results)} results for query: {query[:50]}...")
        return results
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        return []


def expand_graph_seeds(
    seeds: List[str],
    hops: int = 1,
    limit_per_seed: int = 10,
    relation_types: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Expand seeds by traversing relationships and return connected nodes.
    
    This function traverses the graph from seed entities using typed relationships
    (from the typed relationships refactoring) instead of generic RELATION edges.
    
    Args:
        seeds: List of entity names to expand from
        hops: Number of relationship hops to traverse
        limit_per_seed: Maximum neighbors to return per seed
        relation_types: Optional list of relationship types to follow
                       (e.g., ['PART_OF', 'DEFINES']. If None, all types followed)
    
    Returns:
        Dict mapping seed entity name -> list of neighbor dicts {name, relation, source}
        
    Example:
        >>> neighbors = expand_graph_seeds(
        ...     seeds=['Section 420 IPC'],
        ...     hops=2,
        ...     relation_types=['PART_OF', 'DEFINES']
        ... )
    """
    out = {}
    
    try:
        with neo4j_session() as session:
            for seed in seeds:
                # Build relationship pattern for query
                if relation_types:
                    # Use specific typed relationships
                    rel_types_str = "|".join(relation_types)
                    rel_pattern = f"[r:{rel_types_str}]"
                else:
                    # Use any relationship (but prefer typed relationships over generic)
                    rel_pattern = "[r]"
                
                # Query with variable hops (1..hops)
                query = f"""
                MATCH (a:Entity {{name: $name}})-{rel_pattern}*1..{hops}->(b:Entity)
                RETURN DISTINCT b.name as name, type(r) as relation_type, r.source as source
                LIMIT $limit
                """
                
                result = session.run(query, name=seed, limit=limit_per_seed)
                neighbors = []
                
                for record in result:
                    neighbors.append({
                        "name": record.get("name"),
                        "relation": record.get("relation_type"),
                        "source": record.get("source"),
                    })
                
                out[seed] = neighbors
                logger.debug(f"Expanded seed '{seed}' to {len(neighbors)} neighbors")
        
        return out
        
    except Exception as e:
        logger.error(f"Graph expansion failed: {e}")
        return {seed: [] for seed in seeds}


def get_retrieval_stats() -> Dict[str, Any]:
    """Get statistics about vector search capabilities and graph status."""
    try:
        stats = {
            'vector_search': get_vector_search_stats(),
            'graph': {},
        }
        
        # Get graph statistics
        with neo4j_session() as session:
            # Total entities
            result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            record = result.single()
            stats['graph']['total_entities'] = record.get('count', 0) if record else 0
            
            # Entities with embeddings
            result = session.run("MATCH (e:Entity) WHERE e.embedding IS NOT NULL RETURN count(e) as count")
            record = result.single()
            stats['graph']['entities_with_embeddings'] = record.get('count', 0) if record else 0
            
            # Relationship count
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = result.single()
            stats['graph']['total_relationships'] = record.get('count', 0) if record else 0
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get retrieval stats: {e}")
        return {'error': str(e)}
