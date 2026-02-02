"""
Vector Index Manager for Neo4j

Manages vector indexes in Neo4j for efficient semantic search. Provides utilities for:
- Creating vector indexes with proper configuration
- Validating index status and health
- Monitoring index performance and statistics
- Rebuilding corrupted indexes
- Troubleshooting vector search issues

Requirements: Neo4j 5.0+ with vector support
"""

import argparse
import logging
import sys
import time
from typing import Dict, Any, Optional, List

from src.database.neo4j.client import get_neo4j_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorIndexManager:
    """Manages vector indexes in Neo4j."""
    
    DEFAULT_INDEX_NAME = 'entity_embedding_index'
    DEFAULT_NODE_LABEL = 'Entity'
    DEFAULT_PROPERTY = 'embedding'
    DEFAULT_DIMENSIONS = 3072  # text-embedding-3-large
    DEFAULT_SIMILARITY_FUNCTION = 'cosine'
    
    def __init__(self, session=None):
        """Initialize manager with Neo4j session."""
        self.session = session
        self._own_session = session is None
    
    def __enter__(self):
        """Context manager entry."""
        if self._own_session:
            self.session = get_neo4j_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._own_session and self.session:
            self.session.close()
    
    def check_neo4j_version(self) -> Optional[str]:
        """Check Neo4j version and return version string."""
        try:
            if not self.session:
                with get_neo4j_session() as session:
                    result = session.run("CALL dbms.components()")
                    record = result.single()
                    versions = record.get('versions', [])
                    return versions[0] if versions else None
            else:
                result = self.session.run("CALL dbms.components()")
                record = result.single()
                versions = record.get('versions', [])
                return versions[0] if versions else None
        except Exception as e:
            logger.error(f"Failed to check Neo4j version: {e}")
            return None
    
    def check_vector_support(self) -> bool:
        """Check if Neo4j supports vector indexes."""
        try:
            version = self.check_neo4j_version()
            if version:
                major = int(version.split('.')[0])
                if major < 5:
                    logger.warning(f"Neo4j {version} does not support vector indexes (requires 5.0+)")
                    return False
            
            # Try to create a test index
            if not self.session:
                with get_neo4j_session() as session:
                    session.run(
                        """
                        CREATE VECTOR INDEX test_vector_support IF NOT EXISTS
                        FOR (n:_Test) ON (n.embedding)
                        OPTIONS {indexConfig: {`vector.dimensions`: 10, `vector.similarity_function`: 'cosine'}}
                        """
                    )
                    # Clean up
                    session.run("DROP INDEX test_vector_support IF EXISTS")
            else:
                self.session.run(
                    """
                    CREATE VECTOR INDEX test_vector_support IF NOT EXISTS
                    FOR (n:_Test) ON (n.embedding)
                    OPTIONS {indexConfig: {`vector.dimensions`: 10, `vector.similarity_function`: 'cosine'}}
                    """
                )
                self.session.run("DROP INDEX test_vector_support IF EXISTS")
            
            logger.info("Neo4j supports vector indexes")
            return True
        except Exception as e:
            logger.warning(f"Vector support check failed: {e}")
            return False
    
    def create_vector_index(
        self,
        index_name: str = DEFAULT_INDEX_NAME,
        node_label: str = DEFAULT_NODE_LABEL,
        property_name: str = DEFAULT_PROPERTY,
        dimensions: int = DEFAULT_DIMENSIONS,
        similarity_function: str = DEFAULT_SIMILARITY_FUNCTION,
    ) -> bool:
        """
        Create a vector index for semantic search.
        
        Args:
            index_name: Name for the index
            node_label: Neo4j node label to index
            property_name: Property containing embeddings
            dimensions: Embedding vector dimensions
            similarity_function: 'cosine', 'euclidean', or 'dot_product'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.check_vector_support():
                logger.error("Neo4j does not support vector indexes")
                return False
            
            logger.info(f"Creating vector index: {index_name}")
            
            query = f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS
            FOR (n:{node_label}) ON (n.{property_name})
            OPTIONS {{indexConfig: {{`vector.dimensions`: {dimensions}, `vector.similarity_function`: '{similarity_function}'}}}}
            """
            
            session = self.session or get_neo4j_session()
            try:
                result = session.run(query)
                logger.info(f"Vector index '{index_name}' created successfully")
                return True
            finally:
                if not self.session:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            return False
    
    def get_index_status(self, index_name: str = DEFAULT_INDEX_NAME) -> Optional[Dict[str, Any]]:
        """
        Get detailed status of a vector index.
        
        Returns:
            Dict with index info or None if index not found
        """
        try:
            session = self.session or get_neo4j_session()
            try:
                result = session.run(
                    """
                    SHOW INDEXES YIELD name, type, entityType, properties, state
                    WHERE name = $name AND type = 'VECTOR'
                    RETURN name, type, entityType, properties, state
                    """,
                    name=index_name
                )
                record = result.single()
                if record:
                    return dict(record)
                else:
                    logger.warning(f"Vector index '{index_name}' not found")
                    return None
            finally:
                if not self.session:
                    session.close()
        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            return None
    
    def get_index_statistics(self, index_name: str = DEFAULT_INDEX_NAME) -> Dict[str, Any]:
        """Get statistics about the vector index and indexed entities."""
        stats = {
            'index_name': index_name,
            'total_entities': 0,
            'entities_with_embeddings': 0,
            'coverage_percent': 0.0,
        }
        
        try:
            session = self.session or get_neo4j_session()
            try:
                # Total entities
                result = session.run("MATCH (e:Entity) RETURN count(e) as count")
                record = result.single()
                stats['total_entities'] = record.get('count', 0) if record else 0
                
                # Entities with embeddings
                result = session.run(
                    "MATCH (e:Entity) WHERE e.embedding IS NOT NULL RETURN count(e) as count"
                )
                record = result.single()
                stats['entities_with_embeddings'] = record.get('count', 0) if record else 0
                
                # Coverage
                if stats['total_entities'] > 0:
                    stats['coverage_percent'] = (
                        stats['entities_with_embeddings'] / stats['total_entities'] * 100
                    )
                
                logger.info(f"Index statistics: {stats}")
                return stats
            finally:
                if not self.session:
                    session.close()
        except Exception as e:
            logger.error(f"Failed to get index statistics: {e}")
            return stats
    
    def validate_index(self, index_name: str = DEFAULT_INDEX_NAME) -> Dict[str, Any]:
        """
        Validate vector index health and functionality.
        
        Returns:
            Dict with validation results
        """
        results = {
            'valid': True,
            'issues': [],
            'warnings': [],
        }
        
        try:
            # Check if index exists
            status = self.get_index_status(index_name)
            if not status:
                results['valid'] = False
                results['issues'].append(f"Index '{index_name}' does not exist")
                return results
            
            # Check index state
            index_state = status.get('state')
            if index_state != 'ONLINE':
                results['issues'].append(f"Index state is '{index_state}', expected 'ONLINE'")
                results['valid'] = False
            
            # Get statistics
            stats = self.get_index_statistics(index_name)
            
            if stats['total_entities'] == 0:
                results['warnings'].append("No entities found in database")
            
            if stats['entities_with_embeddings'] == 0:
                results['issues'].append("No entities have embeddings")
                results['valid'] = False
            elif stats['coverage_percent'] < 50:
                results['warnings'].append(
                    f"Only {stats['coverage_percent']:.1f}% of entities have embeddings"
                )
            
            logger.info(f"Validation results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            results['valid'] = False
            results['issues'].append(str(e))
            return results
    
    def rebuild_index(
        self,
        index_name: str = DEFAULT_INDEX_NAME,
        node_label: str = DEFAULT_NODE_LABEL,
        property_name: str = DEFAULT_PROPERTY,
        dimensions: int = DEFAULT_DIMENSIONS,
    ) -> bool:
        """
        Rebuild a corrupted or stale vector index.
        
        Args:
            index_name: Name of index to rebuild
            node_label: Node label to re-index
            property_name: Embedding property
            dimensions: Vector dimensions
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Rebuilding vector index: {index_name}")
            
            session = self.session or get_neo4j_session()
            try:
                # Drop existing index
                logger.info(f"Dropping existing index '{index_name}'...")
                session.run(f"DROP INDEX {index_name} IF EXISTS")
                
                # Wait for drop to complete
                time.sleep(2)
                
                # Recreate index
                logger.info(f"Creating new index '{index_name}'...")
                self.create_vector_index(
                    index_name=index_name,
                    node_label=node_label,
                    property_name=property_name,
                    dimensions=dimensions,
                )
                
                # Verify
                time.sleep(2)
                status = self.get_index_status(index_name)
                if status and status.get('state') == 'ONLINE':
                    logger.info("Index rebuild successful")
                    return True
                else:
                    logger.error("Index rebuild failed - index not in ONLINE state")
                    return False
                    
            finally:
                if not self.session:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Index rebuild failed: {e}")
            return False
    
    def test_vector_search(self, query_text: str = "test", top_k: int = 5) -> bool:
        """
        Test vector search functionality with a sample query.
        
        Args:
            query_text: Text to search for (will be embedded)
            top_k: Number of results to return
            
        Returns:
            True if search works, False otherwise
        """
        try:
            from src.database.embeddings import get_embedding_service
            
            logger.info(f"Testing vector search with query: '{query_text}'")
            
            # Get embedding
            emb_service = get_embedding_service()
            query_vector = emb_service.embed_single_text(query_text)
            
            # Try vector search
            session = self.session or get_neo4j_session()
            try:
                result = session.run(
                    """
                    CALL db.index.vector.queryNodes('entity_embedding_index', $top_k, $query_vector)
                    YIELD node as e, score
                    RETURN e.name as name, score
                    LIMIT $top_k
                    """,
                    query_vector=query_vector,
                    top_k=top_k
                )
                
                records = list(result)
                logger.info(f"Vector search returned {len(records)} results")
                
                for record in records:
                    logger.info(f"  - {record.get('name')}: {record.get('score'):.4f}")
                
                return len(records) > 0
                
            finally:
                if not self.session:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Vector search test failed: {e}")
            return False


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='Manage Neo4j vector indexes for semantic search'
    )
    parser.add_argument(
        'action',
        choices=['create', 'status', 'validate', 'rebuild', 'test', 'stats'],
        help='Action to perform'
    )
    parser.add_argument(
        '--index-name',
        default=VectorIndexManager.DEFAULT_INDEX_NAME,
        help='Vector index name'
    )
    parser.add_argument(
        '--node-label',
        default=VectorIndexManager.DEFAULT_NODE_LABEL,
        help='Neo4j node label to index'
    )
    parser.add_argument(
        '--property',
        default=VectorIndexManager.DEFAULT_PROPERTY,
        help='Embedding property name'
    )
    parser.add_argument(
        '--dimensions',
        type=int,
        default=VectorIndexManager.DEFAULT_DIMENSIONS,
        help='Embedding vector dimensions'
    )
    parser.add_argument(
        '--similarity',
        default=VectorIndexManager.DEFAULT_SIMILARITY_FUNCTION,
        choices=['cosine', 'euclidean', 'dot_product'],
        help='Similarity function'
    )
    parser.add_argument(
        '--test-query',
        default='test query',
        help='Query text for testing'
    )
    
    args = parser.parse_args()
    
    try:
        with VectorIndexManager() as manager:
            if args.action == 'create':
                logger.info("Creating vector index...")
                success = manager.create_vector_index(
                    index_name=args.index_name,
                    node_label=args.node_label,
                    property_name=args.property,
                    dimensions=args.dimensions,
                    similarity_function=args.similarity,
                )
                sys.exit(0 if success else 1)
            
            elif args.action == 'status':
                logger.info("Checking vector index status...")
                status = manager.get_index_status(args.index_name)
                if status:
                    for key, value in status.items():
                        print(f"  {key}: {value}")
                    sys.exit(0)
                else:
                    sys.exit(1)
            
            elif args.action == 'stats':
                logger.info("Getting vector index statistics...")
                stats = manager.get_index_statistics(args.index_name)
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                sys.exit(0)
            
            elif args.action == 'validate':
                logger.info("Validating vector index...")
                results = manager.validate_index(args.index_name)
                print(f"\nValid: {results['valid']}")
                if results['issues']:
                    print("Issues:")
                    for issue in results['issues']:
                        print(f"  - {issue}")
                if results['warnings']:
                    print("Warnings:")
                    for warning in results['warnings']:
                        print(f"  - {warning}")
                sys.exit(0 if results['valid'] else 1)
            
            elif args.action == 'rebuild':
                logger.info("Rebuilding vector index...")
                success = manager.rebuild_index(
                    index_name=args.index_name,
                    node_label=args.node_label,
                    property_name=args.property,
                    dimensions=args.dimensions,
                )
                sys.exit(0 if success else 1)
            
            elif args.action == 'test':
                logger.info("Testing vector search...")
                success = manager.test_vector_search(
                    query_text=args.test_query,
                    top_k=5
                )
                sys.exit(0 if success else 1)
    
    except Exception as e:
        logger.error(f"Vector index manager failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
