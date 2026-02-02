#!/usr/bin/env python3
"""
Backfill inferred hierarchical PART_OF_HIERARCHY relations in Neo4j.

Heuristics used:
- For Section nodes missing PART_OF_HIERARCHY, attempt to find a Chapter node
  in the same law_level where the chapter display name is mentioned in the
  section's display_name or source metadata.
- If a match is found, create (section)-[:PART_OF_HIERARCHY {inferred: true}]->(chapter)

Run with NEO4J env vars set.
"""
import os
import logging
from src.database.neo4j.client import neo4j_session

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def backfill(limit: int | None = None):
    with neo4j_session() as session:
        # Find Section nodes without PART_OF_HIERARCHY outgoing
        query = """
        MATCH (s:Entity)
        WHERE s.entity_type = 'Section'
        OPTIONAL MATCH (s)-[p:PART_OF_HIERARCHY]->()
        WITH s, count(p) as outgoing
        WHERE outgoing = 0
        RETURN s.name as name, s.display_name as display_name, s.canonical_id as canonical_id, s.source as source
        """
        if limit:
            query = query + f" LIMIT {int(limit)}"

        records = session.run(query)
        candidates = list(records)
        logger.info(f"Found {len(candidates)} section candidates to attempt backfill")

        matches_created = 0
        for rec in candidates:
            name = rec.get('name')
            display = (rec.get('display_name') or '')
            canonical = rec.get('canonical_id') or ''
            source = rec.get('source') or ''

            # Heuristic: look for chapter nodes in same source that have short display names
            chap_q = """
            MATCH (c:Entity)
            WHERE c.entity_type = 'Chapter' AND c.source = $source
            RETURN c.name as name, c.display_name as display_name, c.canonical_id as canonical_id
            """
            try:
                chaps = list(session.run(chap_q, source=source))
            except Exception:
                chaps = []

            found = False
            for c in chaps:
                c_display = (c.get('display_name') or '')
                if not c_display:
                    continue
                # simple substring match (case-insensitive)
                if c_display.lower() in display.lower():
                    # create inferred relation
                    try:
                        session.run(
                            """
                            MATCH (s:Entity {name: $section_name})
                            MATCH (c:Entity {name: $chapter_name})
                            MERGE (s)-[r:PART_OF_HIERARCHY]->(c)
                            ON CREATE SET r.inferred = true, r.created_at = timestamp(), r.source = $source
                            SET r.relation_confidence = 0.6
                            """,
                            section_name=name,
                            chapter_name=c.get('name'),
                            source=source,
                        )
                        matches_created += 1
                        found = True
                        logger.info(f"Inferred parent {c.get('display_name')} for section {display}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to create inferred relation: {e}")
                        continue

            if not found:
                # try canonical-id prefix matching: if section canonical_id like IPC:Section:420,
                # try to find chapter with same IPC prefix
                if canonical and ':' in canonical:
                    prefix = canonical.split(':')[0]
                    try:
                        q2 = """
                        MATCH (c:Entity)
                        WHERE c.entity_type = 'Chapter' AND c.canonical_id STARTS WITH $prefix
                        RETURN c.name as name, c.display_name as display_name, c.canonical_id as canonical_id LIMIT 1
                        """
                        res = list(session.run(q2, prefix=prefix))
                        if res:
                            c = res[0]
                            session.run(
                                """
                                MATCH (s:Entity {name: $section_name})
                                MATCH (c:Entity {name: $chapter_name})
                                MERGE (s)-[r:PART_OF_HIERARCHY]->(c)
                                ON CREATE SET r.inferred = true, r.created_at = timestamp(), r.source = $source
                                SET r.relation_confidence = 0.6
                                """,
                                section_name=name,
                                chapter_name=c.get('name'),
                                source=source,
                            )
                            matches_created += 1
                            logger.info(f"Inferred parent by canonical prefix {c.get('display_name')} for section {display}")
                            continue
                    except Exception as e:
                        logger.debug(f"Prefix matching failed: {e}")

        logger.info(f"Backfill completed. Matches created: {matches_created}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backfill hierarchical relations in Neo4j')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of sections to examine')
    args = parser.parse_args()
    backfill(limit=args.limit)
