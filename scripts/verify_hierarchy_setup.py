#!/usr/bin/env python3
"""
Verify APOC installation and Neo4j setup for hierarchical entity labeling.

Usage:
    python scripts/verify_hierarchy_setup.py
"""
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

def main():
    print("🔍 Verifying Hierarchical Entity Setup...")
    print("=" * 60)

    # Check environment
    print("\n1️⃣  Environment Variables:")
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_pass = os.getenv('NEO4J_PASSWORD')
    openai_key = os.getenv('OPENAI_API_KEY')

    print(f"   NEO4J_URI: {neo4j_uri}")
    print(f"   NEO4J_USER: {neo4j_user}")
    print(f"   NEO4J_PASSWORD: {'✅ Set' if neo4j_pass else '❌ Not set'}")
    print(f"   OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Not set'}")

    if not neo4j_pass:
        print("\n❌ NEO4J_PASSWORD not set. Cannot connect to Neo4j.")
        return 1

    # Check Neo4j connection
    print("\n2️⃣  Neo4j Connection:")
    try:
        from database.neo4j.client import neo4j_session
        with neo4j_session() as session:
            result = session.run("RETURN 1 as connected")
            result.single()
            print("   ✅ Connected to Neo4j")
    except Exception as e:
        print(f"   ❌ Failed to connect to Neo4j: {e}")
        return 1

    # Check APOC
    print("\n3️⃣  APOC Plugin:")
    try:
        from database.neo4j.client import neo4j_session
        with neo4j_session() as session:
            result = session.run("CALL apoc.version()")
            version_info = result.single()
            print(f"   ✅ APOC is installed: {version_info}")
    except Exception as e:
        print(f"   ❌ APOC not available: {e}")
        print("\n   📝 To install APOC:")
        print("      - Neo4j Desktop: Plugins → APOC Core → Install → Restart")
        print("      - Docker: Copy APOC jar to /var/lib/neo4j/plugins/ and restart")
        print("      - Remote: Check your Neo4j instance admin panel")
        return 1

    # Check ontology
    print("\n4️⃣  Legal Ontology:")
    try:
        from config.legal_ontology import EntityType, LegalOntology
        entity_types = list(EntityType)
        print(f"   ✅ Loaded {len(entity_types)} entity types")
        print(f"      Examples: {', '.join([et.value for et in entity_types[:5]])}")
    except Exception as e:
        print(f"   ❌ Failed to load ontology: {e}")
        return 1

    # Check sample hierarchy in database
    print("\n5️⃣  Sample Hierarchy Check:")
    try:
        from database.neo4j.client import neo4j_session
        with neo4j_session() as session:
            # Count nodes by label
            result = session.run("""
                MATCH (n:Entity)
                WHERE n.entity_type IS NOT NULL
                WITH DISTINCT n.entity_type as entity_type, COUNT(n) as count
                RETURN entity_type, count
                ORDER BY count DESC
                LIMIT 5
            """)
            records = result.data()
            if records:
                print("   ✅ Found entities in database:")
                for rec in records:
                    print(f"      - {rec['entity_type']}: {rec['count']} nodes")
            else:
                print("   ⚠️  No entities found in database (expected if no data ingested yet)")

            # Check for PART_OF_HIERARCHY relations
            result = session.run("""
                MATCH (a)-[r:PART_OF_HIERARCHY]->(b)
                RETURN COUNT(r) as hierarchy_count
            """)
            count = result.single()['hierarchy_count']
            if count > 0:
                print(f"   ✅ Found {count} PART_OF_HIERARCHY relations")
            else:
                print(f"   ⚠️  No PART_OF_HIERARCHY relations found yet")

    except Exception as e:
        print(f"   ⚠️  Could not query database: {e}")

    print("\n" + "=" * 60)
    print("✅ Hierarchy setup verified successfully!")
    print("\nNext steps:")
    print("  1. Run: python scripts/ingest_json_legal_documents.py --directory data/knowledge_base/")
    print("  2. Verify labels with: MATCH (n:Section) RETURN COUNT(n)")
    print("  3. Query hierarchy: MATCH (s:Section)-[:PART_OF_HIERARCHY]->(c:Chapter) RETURN s, c")
    return 0


if __name__ == '__main__':
    sys.exit(main())
