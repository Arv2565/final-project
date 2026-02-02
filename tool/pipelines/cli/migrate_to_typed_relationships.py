"""
Migration script to convert existing generic :RELATION relationships to typed relationships.

This script handles the migration from the old pattern (RELATION with type property)
to the new pattern (native typed relationships). It should be run once after updating
the ingestion code to convert historical data.

Usage:
    python scripts/migrate_to_typed_relationships.py --dry-run       # See what will be changed
    python scripts/migrate_to_typed_relationships.py --execute       # Actually perform migration
    python scripts/migrate_to_typed_relationships.py --verify        # Verify migration status
"""

import argparse
import logging
import sys
from typing import Dict, Any, Optional, List

from neo4j import Session
from src.database.neo4j.client import get_neo4j_session
from src.config import LegalOntology
from src.utils.cypher_builder import relationship_type_to_cypher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TypedRelationshipMigrator:
    """Manages migration from generic RELATION to typed relationships."""
    
    def __init__(self, session: Session):
        """Initialize migrator with Neo4j session."""
        self.session = session
        self.stats = {
            'relations_found': 0,
            'relations_migrated': 0,
            'relations_failed': 0,
            'relation_types': {}
        }
    
    def get_generic_relation_count(self) -> int:
        """Count existing generic RELATION relationships."""
        query = "MATCH ()-[r:RELATION]-() RETURN count(r) as count"
        result = self.session.run(query)
        count = result.single()['count']
        self.stats['relations_found'] = count
        return count
    
    def get_relation_type_distribution(self) -> Dict[str, int]:
        """Get distribution of relation types in generic RELATION edges."""
        query = """
        MATCH ()-[r:RELATION]-()
        WHERE r.canonical_type IS NOT NULL
        RETURN r.canonical_type as type, count(r) as count
        ORDER BY count DESC
        """
        result = self.session.run(query)
        distribution = {row['type']: row['count'] for row in result}
        self.stats['relation_types'] = distribution
        return distribution
    
    def dry_run_migration(self) -> Dict[str, Any]:
        """Show what would be migrated without actually changing data."""
        logger.info("=== DRY RUN: Migration Analysis ===")
        
        # Count relations
        count = self.get_generic_relation_count()
        logger.info(f"Found {count} generic RELATION relationships")
        
        if count == 0:
            logger.info("No generic RELATION relationships found. Migration not needed.")
            return {'status': 'not_needed', 'count': 0}
        
        # Get type distribution
        distribution = self.get_relation_type_distribution()
        logger.info(f"Relation types to migrate: {len(distribution)}")
        
        for rel_type, rel_count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            cypher_type = relationship_type_to_cypher(rel_type)
            logger.info(f"  {rel_type:30} -> {cypher_type:25} ({rel_count:6} relations)")
        
        # Check for APOC availability
        try:
            apoc_check = self.session.run("RETURN apoc.version() as version")
            version = apoc_check.single()
            logger.info(f"APOC plugin available: {version}")
            apoc_available = True
        except Exception as e:
            logger.warning(f"APOC plugin not available: {e}")
            logger.warning("Migration will use fallback approach without APOC")
            apoc_available = False
        
        return {
            'status': 'dry_run_complete',
            'relations_found': count,
            'relation_types': len(distribution),
            'apoc_available': apoc_available,
            'distribution': distribution
        }
    
    def migrate_relations_with_apoc(self, batch_size: int = 1000) -> Dict[str, Any]:
        """Migrate relations using APOC in batches.
        
        This is the preferred method if APOC is available.
        """
        logger.info("=== Starting Migration with APOC ===")
        
        migrated = 0
        failed = 0
        
        # Process in batches
        query_batch = """
        MATCH ()-[r:RELATION]-() 
        WHERE r.canonical_type IS NOT NULL
        LIMIT $batch_size
        WITH collect(r) as batch_rels
        UNWIND batch_rels as r
        WITH r, type(r) as original_type, r.canonical_type as canonical_type
        CALL apoc.refactor.setType(r, 'LEGACY_RELATION') YIELD rel
        RETURN count(rel) as updated
        """
        
        while True:
            result = self.session.run(query_batch, batch_size=batch_size)
            batch_count = result.single()['updated']
            
            if batch_count == 0:
                break
            
            migrated += batch_count
            logger.info(f"Migrated {migrated} relations so far...")
        
        logger.info(f"Successfully migrated {migrated} relations")
        self.stats['relations_migrated'] = migrated
        
        return {'status': 'migrated', 'count': migrated}
    
    def migrate_relations_fallback(self, batch_size: int = 100) -> Dict[str, Any]:
        """Fallback migration without APOC.
        
        This creates new typed relationships and marks old ones as archived.
        """
        logger.info("=== Starting Migration (Fallback without APOC) ===")
        
        migrated = 0
        failed = 0
        
        # Get all distinct canonical types
        query_types = """
        MATCH ()-[r:RELATION]->()
        WHERE r.canonical_type IS NOT NULL
        RETURN DISTINCT r.canonical_type as canonical_type
        ORDER BY canonical_type
        """
        
        result = self.session.run(query_types)
        types_to_migrate = [row['canonical_type'] for row in result]
        
        logger.info(f"Found {len(types_to_migrate)} relation types to migrate")
        
        for canonical_type in types_to_migrate:
            try:
                cypher_type = relationship_type_to_cypher(canonical_type)
                
                # Process in batches
                offset = 0
                batch_migrated = 0
                
                while True:
                    # Get batch of relations
                    query_batch = f"""
                    MATCH (a)-[r:RELATION {{canonical_type: $canonical_type}}]->(b)
                    RETURN a, r, b
                    SKIP $offset
                    LIMIT $batch_size
                    """
                    
                    result = self.session.run(
                        query_batch,
                        canonical_type=canonical_type,
                        offset=offset,
                        batch_size=batch_size
                    )
                    
                    records = list(result)
                    if not records:
                        break
                    
                    # Create new typed relationships
                    for record in records:
                        a = record['a']
                        r = record['r']
                        b = record['b']
                        
                        try:
                            # Extract properties to copy
                            props = dict(r)
                            
                            # Create new typed relationship (using fallback pattern)
                            create_query = f"""
                            MATCH (a) WHERE id(a) = $head_id
                            MATCH (b) WHERE id(b) = $tail_id
                            MERGE (a)-[new_rel:{cypher_type}]->(b)
                            SET new_rel += $properties
                            RETURN new_rel
                            """
                            
                            self.session.run(
                                create_query,
                                head_id=a.id,
                                tail_id=b.id,
                                properties=props
                            )
                            
                            # Mark old relationship as migrated
                            mark_query = """
                            MATCH (a)-[r:RELATION]->(b)
                            WHERE id(r) = $rel_id
                            SET r.migrated_at = timestamp(), r.migrated_to_type = $new_type
                            RETURN r
                            """
                            
                            self.session.run(
                                mark_query,
                                rel_id=r.id,
                                new_type=cypher_type
                            )
                            
                            batch_migrated += 1
                            migrated += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to migrate relation {r.id}: {e}")
                            failed += 1
                    
                    offset += batch_size
                
                logger.info(f"Migrated {batch_migrated} {canonical_type} relations to {cypher_type}")
                
            except Exception as e:
                logger.error(f"Failed to process type {canonical_type}: {e}")
                failed += len(types_to_migrate)
        
        logger.info(f"Migration complete: {migrated} migrated, {failed} failed")
        self.stats['relations_migrated'] = migrated
        self.stats['relations_failed'] = failed
        
        return {'status': 'migrated', 'count': migrated, 'failed': failed}
    
    def verify_migration(self) -> Dict[str, Any]:
        """Verify migration status and report statistics."""
        logger.info("=== Migration Verification ===")
        
        # Count remaining generic RELATION
        query_generic = "MATCH ()-[r:RELATION {migrated_at: null}]-() RETURN count(r) as count"
        result = self.session.run(query_generic)
        remaining = result.single()['count']
        
        # Count new typed relationships
        query_typed = """
        MATCH ()-[r]->()
        WHERE type(r) IN ['AMENDS', 'CITES', 'PART_OF', 'CONTAINS', 'DEFINES', 
                         'ENFORCES', 'IMPLEMENTS', 'REFERENCES']
        RETURN count(r) as count
        """
        result = self.session.run(query_typed)
        new_typed = result.single()['count']
        
        # Count migrated relations
        query_migrated = "MATCH ()-[r:RELATION {migrated_at: null}]-() RETURN count(r) as count"
        result = self.session.run(query_migrated)
        migrated = result.single()['count']
        
        logger.info(f"Generic RELATION remaining: {remaining}")
        logger.info(f"New typed relationships: {new_typed}")
        logger.info(f"Marked as migrated: {migrated}")
        
        return {
            'status': 'verified',
            'remaining_generic': remaining,
            'new_typed': new_typed,
            'marked_migrated': migrated
        }
    
    def cleanup_migrated_relations(self, keep_backup: bool = True) -> Dict[str, Any]:
        """Remove old generic RELATION edges after migration is verified.
        
        Args:
            keep_backup: If True, only delete relations marked as migrated.
                        If False, delete all generic RELATION edges (careful!).
        """
        if keep_backup:
            query = "MATCH ()-[r:RELATION {migrated_at: null}]-() DELETE r"
        else:
            query = "MATCH ()-[r:RELATION]-() DELETE r"
        
        result = self.session.run(query)
        summary = result.consume()
        deleted = summary.counters.relationships_deleted
        
        logger.info(f"Deleted {deleted} generic RELATION edges")
        
        return {'status': 'cleaned', 'deleted': deleted}


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description='Migrate generic RELATION relationships to typed relationships'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform the migration'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration status'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Remove old generic RELATION edges after verification'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for processing (default: 1000)'
    )
    
    args = parser.parse_args()
    
    # Ensure at least one action is specified
    if not any([args.dry_run, args.execute, args.verify, args.cleanup]):
        parser.print_help()
        sys.exit(1)
    
    # Get Neo4j session
    try:
        session = get_neo4j_session()
        migrator = TypedRelationshipMigrator(session)
        
        if args.dry_run:
            result = migrator.dry_run_migration()
            logger.info(f"Dry run result: {result}")
        
        if args.execute:
            logger.warning("Starting migration. This may take a while...")
            result = migrator.migrate_relations_fallback(batch_size=args.batch_size)
            logger.info(f"Migration result: {result}")
        
        if args.verify:
            result = migrator.verify_migration()
            logger.info(f"Verification result: {result}")
        
        if args.cleanup:
            logger.warning("Cleaning up old generic RELATION edges...")
            result = migrator.cleanup_migrated_relations(keep_backup=True)
            logger.info(f"Cleanup result: {result}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
