# Graph Indexing Strategy (GraphRAG)

## Overview
This project builds a dual-retrieval graph index (GraphRAG) that extracts structured triples from documents and stores them in Neo4j. Optionally, entity text is embedded and stored as vectors to enable semantic search alongside structured graph queries.

## Goals
- Convert unstructured documents (JSON, TXT, PDF) into a structured knowledge graph.
- Maintain a lightweight, validated triple model (head, relation, tail).
- Support both structured graph traversal (Neo4j) and semantic retrieval via vector similarity.
- Track costs and progress when using LLMs/embeddings.

## Data model
- Node label: `Entity`
  - key property: `name` (unique per entity via MERGE)
  - optional: `embedding` (vector), `last_embedded_at`
- Relationship type: `RELATION`
  - property: `type` (relation name)
  - metadata: `source` (origin file path), `chunk_id`, `created_at`

Triple model (Pydantic validated):
- head: string
- relation: string
- tail: string

## Extraction pipeline
1. Text preparation
   - JSON: flattened to "path: value" lines
   - TXT: read with unicode-safe defaults
   - PDF: extracted with project PDF extractor
   - Coalesce into ~100-word paragraphs for LLM-friendly chunks
2. Chunking
   - Controlled by processing config: chunk size and overlap
   - Prescan stage estimates total chunks for progress/ETA
3. LLM triple extraction
   - System + user prompts ask for JSON-only output containing triples
   - Responses sanitized: remove code fences, parse JSON, validate with Pydantic
   - Low temperature for deterministic extraction
4. Validation & sanitation
   - Each triple must have non-empty head, relation, tail
   - Invalid triples are skipped

## Ingestion & indexing (Neo4j)
- Use MERGE to create/ensure `Entity` nodes and relationships:
  - MERGE (a:Entity {name: $head})
  - MERGE (b:Entity {name: $tail})
  - MERGE (a)-[r:RELATION {type: $rel}]->(b)
- Store provenance: `r.source`, `r.chunk_id`, and `r.created_at`
- Wrap DB operations in a session context for safe connect/close
- Optionally create a native vector index (if Neo4j supports it):
  - CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS FOR (e:Entity) ON (e.embedding)

## Embeddings & vector index
- Embeddings model: project uses OpenAI `text-embedding-3-large` (3072d)
- Batch embedding process:
  - Deduplicate entity names before embedding
  - Batch size configurable (example uses 128)
  - Persist embeddings on nodes: `e.embedding = $embedding`
  - Track token usage and estimate costs
- When Neo4j native vector index unavailable, fall back to other vector DBs or store embeddings for export.

## Cost & progress tracking
- Track tokens for chat prompt/output and embeddings to estimate USD costs.
- Prescan to estimate total chunks; log progress, ETA, rate, and estimated cost during run.

## Query patterns / examples
- Find direct relations:
  - MATCH (a:Entity {name: 'X'})-[r:RELATION]->(b:Entity) RETURN r,b
- Two-hop traversal:
  - MATCH (a:Entity {name:'X'})-[:RELATION]->(b)-[:RELATION]->(c) RETURN b,c
- Combine semantic + graph:
  - Obtain vector-nearest entities (via Neo4j vector index or external search)
  - Use results as seeds for graph traversal to expand context

## Operational notes
- Validate env vars for OpenAI and Neo4j before running CLI.
- Use `max_chunks_per_file` for quick tests to limit LLM calls.
- Keep embedding batch size tuned to memory and rate limits.
- Log failures per chunk and continue processing other chunks/files.
- Periodically re-embed nodes if underlying entity text changes.

## Maintenance & scaling
- Periodic deduplication: normalize entity names (case, whitespace) to avoid node proliferation.
- Backups: export Neo4j graph snapshots; export embeddings for migration.
- Monitoring: track queue sizes, LLM error rates, token-based costs, and Neo4j performance.
- Compatibility: surround vector-index creation with try/except — older Neo4j versions may not support native vectors.

## CLI & integration pointers
- scripts/graph_rag_index.py: entry point for indexing directories or files
- Key switches:
  - --no-embed : skip embedding step
  - --max-chunks : limits chunks per file (useful for development)
- Ensure OPENAI_API_KEY and NEO4J_* credentials are set in env before running.

## Appendix: Best practices
- Use deterministic prompts and strict output schema to simplify parsing.
- Deduplicate entities before embedding to save cost.
- Keep embeddings optional; use them when semantic search is required.
- Store provenance per relationship for traceability back to source documents.
