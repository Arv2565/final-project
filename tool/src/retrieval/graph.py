"""
Graph-based retrieval using Neo4j knowledge graph.

Retrieves entities and relationships from the knowledge graph,
optionally using vector search for entity embeddings.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from .base import GraphRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class Neo4jGraphRetriever(GraphRetriever):
    """
    Graph retrieval using Neo4j knowledge graph.
    
    Retrieves legal entities and their relationships using:
    - Vector search for entity embeddings (text-embedding-3-large)
    - Graph traversal for relationship expansion
    - Type-specific matching for legal entities
    """
    
    def __init__(self, vector_index: str = "entity_embedding_index"):
        """
        Initialize Neo4j-based graph retriever.
        
        Args:
            vector_index: Name of Neo4j vector index for entities
        """
        self.vector_index = vector_index
        self._neo4j_driver = None
        self._embedding_client = None
        self._init_clients()
    
    def _init_clients(self) -> None:
        """Initialize Neo4j driver and OpenAI client."""
        try:
            from src.database.neo4j.client import get_neo4j_driver
            from src.config import get_openai_client
            
            self._neo4j_driver = get_neo4j_driver()
            self._embedding_client = get_openai_client()
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j retriever: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI text-embedding-3-large embedding for text."""
        if not self._embedding_client:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
            response = self._embedding_client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        hops: int = 1,
        filters: Optional[Dict[str, Any]] = None,
        source_filter: Optional[str] = None,
        include_chunks: bool = True,
        max_chunks: int = 5,
        resolution_depth: int = 1,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve entities, relationships, AND text context from graph.
        
        Uses adaptive traversal:
        1. Semantic expansion (1 hop standard)
        2. Structural expansion (recursive parent lookup up to `resolution_depth`)
        3. Context retrieval (fetching text chunks for grounded RAG)
        
        Args:
            query: Query text (entity name or description)
            top_k: Number of entities to return
            hops: Number of semantic hops (default 1)
            filters: Optional entity type filters
            source_filter: Optional source/document name filter
            include_chunks: Whether to fetch text chunks (default True)
            max_chunks: Max chunks to return per entity
            resolution_depth: How far up the hierarchy to traverse (default 1)
            
        Returns:
            RetrievalResult with entities, relationships, and context_chunks
        """
        start_time = time.time()
        
        try:
            # Get query embedding
            query_embedding = self.get_embedding(query)
            
            # Search entities using vector index
            with self._neo4j_driver.session() as session:
                # Vector search for similar entities
                # Note: We filter by source early if possible
                source_clause = f"AND node.source CONTAINS '{source_filter}'" if source_filter else ""
                
                cypher_query = f"""
                CALL db.index.vector.queryNodes('{self.vector_index}', {top_k}, {query_embedding})
                YIELD node, score
                WHERE score > 0.7 {source_clause}
                RETURN node.name as entity_name, node.type as entity_type, node.source as source, score
                limit {top_k}
                """
                
                entities = session.run(cypher_query).data()
                
                results = []
                all_context_chunks = []
                
                for entity in entities:
                    # 1. Expand Semantic & Structural Neighbors
                    expanded = self.expand_entity_neighbors(
                        entity['entity_name'],
                        hops=hops,
                        structural_depth=resolution_depth
                    )
                    
                    # 2. Fetch Text Chunks (Context)
                    if include_chunks:
                        chunks = self._fetch_context_chunks(session, entity['entity_name'], max_chunks)
                        expanded['chunks'] = chunks
                        all_context_chunks.extend(chunks)
                        
                    results.append(expanded)
            
            retrieval_time = (time.time() - start_time) * 1000
            
            # Return enriched result
            # Note: RetrievalResult likely needs to be updated to support 'chunks' or we pack it in metadata
            return RetrievalResult(
                query=query,
                results=results,
                retrieval_type="graph_rag",
                total_results=len(all_context_chunks),
                retrieval_time_ms=retrieval_time,
                metadata={"context_chunks": all_context_chunks} # Store flat list for easy consumption
            )
            
        except Exception as e:
            logger.error(f"Graph retrieval error: {e}", exc_info=True)
            raise
    
    def expand_entity_neighbors(
        self,
        entity_id: str,
        hops: int = 1,
        structural_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Expand entity using Adaptive Traversal strategies.
        
        Strategies:
        1. Semantic: (e)-[r]-(n) where r is generic or semantic (1 hop)
        2. Structural: (e)-[:PART_OF|SECTION_IN|...*]->(parent) recursive up
        
        Handles Bidirectional relationships using `inverse_of` property.
        """
        try:
            with self._neo4j_driver.session() as session:
                # Structural types from documentation (Exact match)
                structural_types = "PART_OF|CONTAINS|CHAPTER_IN|SECTION_IN|SUBSECTION_OF|BELONGS_TO"
                
                # Combined Query:
                # Part A: Immediate Neighbors (Semantic 1-hop)
                # Part B: Recursive Parents (Structural up to depth)
                cypher_query = f"""
                MATCH (e:Entity {{name: $name}})
                
                // 1. Semantic Expansion (Bidirectional)
                OPTIONAL MATCH (e)-[r]-(neighbor)
                WHERE NOT type(r) IN split($structural_types, "|") 
                WITH e, collect({{
                    neighbor: neighbor.name, 
                    rel_type: type(r),
                    direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END,
                    inverse_of: r.inverse_of,
                    confidence: r.relation_confidence
                }}) as semantic_rels
                
                // 2. Structural Expansion (Recursive Upwards)
                MATCH (e)
                OPTIONAL MATCH path = (e)-[:{structural_types}*1..{structural_depth}]->(parent)
                WITH e, semantic_rels, collect([n in nodes(path) | n.name][1..]) as hierarchy_paths
                
                RETURN {{
                    entity: e.name, 
                    type: e.entity_type,
                    semantic_connections: semantic_rels,
                    hierarchy: hierarchy_paths
                }} as expanded_data
                """
                
                result = session.run(cypher_query, name=entity_id, structural_types=structural_types).single()
                
                if result:
                    return result['expanded_data']
                return {}
                    
        except Exception as e:
            logger.error(f"Failed to expand neighbors for {entity_id}: {e}")
            return {"error": str(e)}

    def _fetch_context_chunks(self, session, entity_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Fetch text chunks linked to the entity via MENTIONED_IN.
        """
        query = """
        MATCH (e:Entity {name: $name})-[:MENTIONED_IN]->(c:Chunk)
        RETURN c.text as text, c.source as source, c.id as chunk_id
        LIMIT $limit
        """
        try:
            results = session.run(query, name=entity_name, limit=limit).data()
            return results
        except Exception as e:
            logger.warning(f"Failed to fetch chunks for {entity_name}: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if Neo4j is available."""
        try:
            if not self._neo4j_driver:
                return False
            with self._neo4j_driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Get health status of Neo4j."""
        try:
            with self._neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (n:Entity) RETURN count(n) as entity_count
                """).single()
                
                entity_count = result['entity_count'] if result else 0
                
                return {
                    "status": "healthy",
                    "backend": "neo4j",
                    "entity_count": entity_count,
                    "vector_index": self.vector_index
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "neo4j",
                "error": str(e)
            }
