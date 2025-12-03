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
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve entities and relationships from graph.
        
        Args:
            query: Query text (entity name or description)
            top_k: Number of entities to return
            hops: Number of relationship hops to expand
            filters: Optional entity type filters
            
        Returns:
            RetrievalResult with matched entities and relationships
        """
        start_time = time.time()
        
        try:
            # Get query embedding
            query_embedding = self.get_embedding(query)
            
            # Search entities using vector index
            with self._neo4j_driver.session() as session:
                # Vector search for similar entities
                cypher_query = f"""
                CALL db.index.vector.queryNodes('{self.vector_index}', {top_k}, {query_embedding})
                YIELD node, score
                RETURN node.name as entity_name, node.type as entity_type, score
                LIMIT {top_k}
                """
                
                entities = session.run(cypher_query).data()
                
                # Expand with relationships if requested
                results = []
                for entity in entities:
                    expanded = self.expand_entity_neighbors(
                        entity['entity_name'],
                        hops=hops
                    )
                    results.append(expanded)
            
            retrieval_time = (time.time() - start_time) * 1000
            
            return RetrievalResult(
                query=query,
                results=results,
                retrieval_type="graph",
                total_results=len(results),
                retrieval_time_ms=retrieval_time
            )
            
        except Exception as e:
            logger.error(f"Graph retrieval error: {e}", exc_info=True)
            raise
    
    def expand_entity_neighbors(
        self,
        entity_id: str,
        hops: int = 1
    ) -> Dict[str, Any]:
        """
        Expand entity with its neighbors in the graph.
        
        Args:
            entity_id: Entity identifier
            hops: Number of relationship hops
            
        Returns:
            Dictionary with entity and its neighbors
        """
        try:
            with self._neo4j_driver.session() as session:
                # Match entity and get relationships
                cypher_query = f"""
                MATCH (e:Entity {{name: '{entity_id}'}})
                OPTIONAL MATCH (e)-[r]-(neighbor)
                RETURN e as entity, collect({{
                    rel_type: type(r),
                    neighbor: neighbor.name
                }}) as relationships
                LIMIT {hops}
                """
                
                result = session.run(cypher_query).single()
                
                if result:
                    return {
                        "entity": dict(result['entity']),
                        "relationships": result['relationships']
                    }
                else:
                    return {"entity": None, "relationships": []}
                    
        except Exception as e:
            logger.error(f"Failed to expand neighbors: {e}")
            return {"entity": None, "relationships": []}
    
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
