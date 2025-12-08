# GraphRAG Features & Implementation Logic

This document explains how the **GraphRAG** portion of the Legal RAG system works:

- What the legal knowledge graph represents
- How documents are converted into entities and relationships
- How entity resolution and typed relationships are implemented
- How vector search and graph traversal are combined at query time

It is the primary technical reference for anyone modifying or extending the graph pipeline.

---

## 1. Conceptual Overview

### 1.1 Goals

The GraphRAG subsystem is designed to:

1. Model statutes, sections, cases, procedures, and other legal concepts as a **typed Neo4j graph**
2. Maintain **canonical identifiers** for legal entities (e.g. `IPC:Section:420`, `AIR_1970_SC_1876`)
3. Encode legal semantics using **92+ typed relationship kinds** (e.g. `AMENDS`, `CITES`, `PART_OF`)
4. Support **efficient retrieval** by:
   - Hierarchical traversals (e.g. Section → Chapter → Act)
   - Citation and amendment paths (e.g. Case → CITES → Section)
   - Hybrid vector + graph search

### 1.2 High-Level Flow

At a high level, indexing follows this pipeline:

1. **Ingest documents** (JSON, PDF, etc.)
2. **Flatten / chunk text** into manageable contexts
3. **LLM triple extraction**: GPT‑4o‑mini extracts `(head, relation, tail)` triples with types
4. **Ontology normalization** using `LegalOntology`
5. **Entity resolution** to canonical IDs via `EntityResolver`
6. **Graph ingestion** into Neo4j with typed relationships and properties
7. **Optional embedding** of entities and creation of a vector index

---

## 2. Data Model

### 2.1 Entities (Nodes)

Nodes are stored as `:Entity` plus one or more semantic labels (`:Section`, `:Act`, `:Case`, etc.).

**Key properties** (typical):

- `canonical_id`: stable identifier (e.g. `IPC:Section:420`)
- `name`: machine‑friendly normalized name (`section_420`)
- `display_name`: human‑readable name (`Section 420 IPC`)
- `entity_type`: ontology type string from `EntityType` enum
- `law_level`: where in the hierarchy the node sits (e.g. `statute`, `chapter`)
- `source`: original file / dataset
- `embedding`: optional vector when entity embeddings are enabled

Example conceptual Cypher (simplified):

```cypher
MERGE (s:Entity:Section {
  canonical_id: "IPC:Section:420"
})
SET s.name = "section_420",
    s.display_name = "Section 420 IPC",
    s.entity_type = "Section",
    s.law_level = "statute",
    s.source = "ipc.json"
```

### 2.2 Relationships (Edges)

Relationships model legal semantics and are **typed** using native Neo4j relationship types.

Two key categories:

1. **Hierarchy / structure**
   - `:PART_OF_HIERARCHY` edges connect sections → chapters → acts, etc.
2. **Semantic / legal relations**
   - 92+ types such as `AMENDS`, `CITES`, `DEFINES`, `PENALIZES`, `ENFORCES`, `PROCEDURE_FOR`, etc.

All relations carry at least:

- `relation_confidence` (float, typically 0.5–1.0)
- `source` (file or pipeline stage)
- `created_at` (timestamp)

Example (semantic typed relation):

```cypher
MATCH (a:Section {canonical_id: "IPC:Section:420"}),
      (b:Offence {canonical_id: "IPC:Offence:Cheating"})
MERGE (a)-[r:PENALIZES]->(b)
SET r.relation_confidence = 0.95,
    r.source = "ipc.json",
    r.created_at = timestamp()
```

The mapping from canonical relation names (e.g. `"amends"`) to Neo4j labels (e.g. `"AMENDS"`) is defined in `src/config/legal_ontology.py`.

---

## 3. Triple Extraction & Normalization

### 3.1 Triple Model (`Triple` in `graph_rag_indexer.py`)

The central data structure for extracted relations is the `Triple` Pydantic model:

- `head`: subject entity name
- `relation`: raw relation string from the LLM (later normalized)
- `tail`: object entity name
- `head_type`, `tail_type`: optional entity type hints (default `OTHER`)
- `relation_confidence`: numeric confidence (0.5–1.0)
- `head_canonical_id`, `tail_canonical_id`: optional canonical IDs
- `effective_from`, `effective_to`: optional temporal validity strings

Key behaviors:

- **Validation**: `field_validator`s ensure `head`, `tail`, and `relation` are non‑empty
- **Normalization**: `normalize_and_validate()` converts `relation` to a canonical value using `LegalOntology.normalize_relation` and clamps confidence
- **Ontology checks**: invalid `head_type` / `tail_type` values are replaced with `EntityType.OTHER`

The `Triple` model is the bridge between raw LLM JSON and the strongly typed legal ontology used in the graph.

### 3.2 Flattening and Chunking

Before calling the LLM, documents are normalized:

1. **`flatten_json`**
   - Recursively flattens nested JSON into `"path: value"` lines (keys contain hierarchy context).
2. **`chunk_text`**
   - Splits flattened text into word‑bounded chunks with overlap to control context window usage.

These chunks, along with document‑level hints (e.g. IPC vs Constitution), form the prompt for the chat model.

### 3.3 Prompting & Extraction

`graph_rag_indexer.py` builds a domain‑aware prompt that includes:

- A summary of the **legal ontology** (`EntityType`, `RelationType`)
- Few‑shot examples drawn from real legal texts
- Constraints on output format (strict JSON with `head`, `relation`, `tail`, types, and confidence)

The OpenAI client (`OpenAI` from `openai` package) is used to:

- Call the chat model (`OPENAI_CHAT_MODEL`, e.g. `gpt-4o-mini`)
- Track token/price usage via `CostStats`
- Retry transient failures

Each LLM response is parsed into `Triple` instances, validated, normalized, and either:

- **Accepted** for ingestion, or
- **Flagged** by `flag_uncertain_triples` (via `human_validation` helpers) for manual review if confidence/structure are suspect

---

## 4. Entity Resolution & Canonical IDs

### 4.1 Motivation

Generic fuzzy matching (e.g. 85% similarity) leads to heavy duplication:

- `"Section 420 IPC"`, `"Sec 420 IPC"`, and `"420 IPC"` all create separate nodes
- Case citations in different reporter formats are not linked

This breaks hierarchy inference and pollutes query results.

### 4.2 Legal-Specific Parsers (`docs/ENTITY_RESOLUTION.md`)

The system replaces naive fuzzy matching with **legal‑aware parsers** (see `src/utils/legal_entity_parser.py`):

- `SectionParser` → `IPC:Section:420`, `CRPC:Section:125(1)`
- `CaseCitationParser` → `AIR_1970_SC_1876`, `SCC_2012_SC_1`, etc.
- `StatuteParser` → `IPC`, `IPC:1860`, `CRPC:1973`, `COI`

Each parser returns structured objects containing:

- Raw text
- Statute/citation metadata
- Canonical ID
- Confidence score

### 4.3 EntityResolver Integration

`EntityResolver` (see `src/utils/entity_resolver.py`) maintains a deduplication index.

Typical usage pattern:

```python
from src.utils.entity_resolver import EntityResolver

resolver = EntityResolver(strict_mode=False)

canonical_id = resolver.get_canonical_id("Section 420 IPC")    # "IPC:Section:420"
cluster = resolver.get_cluster_info("IPC:Section:420")          # variants, stats, etc.
```

The enrichment workflow exposes a higher‑level helper:

```python
from src.workflows.graphs.enrichment import canonicalize_entities_legal

names = ["Section 420 IPC", "Sec 420 IPC", "420 IPC"]
name_to_canonical, canonical_to_variants = canonicalize_entities_legal(
    names,
    entity_type="Section",
)
```

During graph ingestion, the indexer:

1. Resolves `head` and `tail` text to canonical IDs
2. Creates/merges nodes keyed on `canonical_id`
3. Stores variants for auditability

This yields ~90% duplicate reduction and significantly smaller/faster graphs.

---

## 5. Typed Relationships & Ontology

### 5.1 From Generic to Typed Relationships

Original pattern (anti‑pattern):

```cypher
MATCH (a)-[r:RELATION {type: 'amends'}]->(b)
RETURN a, r, b
```

Problems:

- All edges share the same label `RELATION`
- Type filtering happens via properties (slower)
- Neo4j cannot optimize as well

New pattern (best practice):

```cypher
MATCH (a)-[r:AMENDS]->(b)
RETURN a, r, b
```

Benefits:

- Fast type‑based matching using native relationship labels
- 12–17× improvement in many query patterns
- Semantically descriptive edge types

### 5.2 Mapping & Helpers

`src/config/legal_ontology.py` defines:

- `RelationType` enum: canonical relation names (e.g. `amends`, `cites`, `penalizes`)
- `RELATION_TO_CYPHER_TYPE` mapping: canonical name → Cypher label (e.g. `"amends" → "AMENDS"`)

Helper:

```python
from src.config.legal_ontology import LegalOntology

cypher_type = LegalOntology.relation_to_cypher_type("amends")   # "AMENDS"
```

The indexer uses this when building Cypher and APOC calls.

### 5.3 Ingestion Strategy (Simplified)

For each validated triple:

1. Resolve `head`/`tail` to canonical IDs and types
2. Look up Neo4j labels for entity types
3. Map canonical relation to Cypher relationship label
4. Merge nodes and create typed relationship

Pseudocode sketch:

```python
head_id = resolver.get_canonical_id(triple.head, triple.head_type)
tail_id = resolver.get_canonical_id(triple.tail, triple.tail_type)
rel_type = LegalOntology.relation_to_cypher_type(triple.relation)

# Merge nodes by canonical_id and connect with typed edge
cypher = """
MERGE (a:Entity {canonical_id: $head_id})
MERGE (b:Entity {canonical_id: $tail_id})
CALL apoc.create.relationship(a, $rel_type, {
  source: $source,
  relation_confidence: $conf,
  created_at: timestamp()
}, b) YIELD rel
RETURN rel
"""
```

If APOC is unavailable, the system falls back to a generic pattern, but with degraded performance (see `docs/TYPED_RELATIONSHIPS_GUIDE.md`).

---

## 6. Vector Search in the Graph Context

While the main vector store for chunks is Qdrant, the graph can also use Neo4j’s **native vector index** so that entities themselves are searchable by embedding.

### 6.1 Neo4j Vector Index

Vector index creation (conceptual Cypher):

```cypher
CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 3072,
  `vector.similarity_function`: 'cosine'
}}
```

This is managed by `scripts/vector_index_manager.py`, which can:

- Create / rebuild the index
- Report coverage and health
- Run basic search benchmarks

### 6.2 Vector Retrieval API

`src/utils/vector_retrieval.py` and `src/workflows/graphs/retrieval.py` expose helpers like:

- `vector_search(query_vector, top_k=10, filters=None, similarity_threshold=0.0)`
- `vector_search_batch(queries, top_k=10)`
- `vector_nearest_entities(query, top_k=10, entity_type_filter=None)`

These functions automatically:

1. Detect whether a Neo4j vector index is available
2. Use native ANN search when possible, with Python cosine fallback otherwise

### 6.3 Adaptive Retrieval (Graph RAG)

The system uses an **Adaptive Traversal** strategy (`Neo4jGraphRetriever`) to combine semantic precision with structural context:

1.  **Semantic Expansion (1-hop)**:
    -   Finds immediate neighbors via any relationship type (e.g., `AMENDS`, `CITES`, `PENALIZES`).
    -   **Bidirectional**: Checks both incoming and outgoing edges, using `inverse_of` properties to correctly label direction.

2.  **Structural Expansion (Recursive)**:
    -   Automatically traverses *up* the hierarchy using specific structural types: `PART_OF`, `SECTION_IN`, `CHAPTER_IN`, `CONTAINS`, `SUBSECTION_OF`, `BELONGS_TO`.
    -   **Goal**: If a specific Section is found, this expansion grabs the Chapter and Act it belongs to, providing broader context to the LLM.

3.  **Context Chunk Retrieval**:
    -   For every identified entity, the system traverses `[:MENTIONED_IN]` edges to fetch the actual **text chunks**.
    -   This provides the "Ground Truth" for RAG generation.

### 6.4 Retrieval API Usage

The unified retrieval API supports advanced filtering and context fetching:

```python
from src.retrieval.graph import Neo4jGraphRetriever

retriever = Neo4jGraphRetriever()

results = retriever.retrieve(
    query="fraud penalties",
    top_k=5,
    hops=1,                         # Semantic hops
    resolution_depth=2,             # Structural depth (Entity -> Chapter -> Act)
    include_chunks=True,            # Fetch text chunks?
    max_chunks=3,                   # Chunks per entity
    source_filter="IPC",            # Filter by document source
    valid_date="2023-01-01"         # Temporal validity check
)

# Result Structure:
# {
#   "query": "fraud penalties",
#   "results": [
#     {
#       "entity": {"name": "Section 420", "type": "Section"},
#       "chunks": [{"text": "Whoever cheats...", "source": "IPC.pdf"}],
#       "hierarchy": ["Chapter XVII", "IPC"],
#       "semantic_connections": [...]
#     }
#   ]
# }
```

---

## 7. Indexing Entry Point (`scripts/graph_rag_index.py`)

The script `scripts/graph_rag_index.py` is the main CLI for building the graph index.

### 7.1 Key CLI Options

Typical flags (see `--help` for the full set):

- `--paths`: file or directory paths to index (supports `--recursive`)
- `--no-embed`: skip embedding entities (graph only, faster)
- `--max-chunks`: cap chunks per run for experimentation
- `--dry-run`: validate pipeline without writing to Neo4j (if implemented)

Example runs:

```bash
# Full index with embeddings
python scripts/graph_rag_index.py --paths data/knowledge_base/ --recursive

# Graph‑only experiment on a subset
python scripts/graph_rag_index.py --paths data/ --max-chunks 50 --no-embed
```

### 7.2 Runtime Statistics

`IndexStats` and `CostStats` in `graph_rag_indexer.py` track:

- Files processed
- Chunks processed
- Triples extracted
- Nodes embedded
- Token usage and estimated OpenAI cost

These stats are logged to help you monitor cost and performance.

---

## 8. Extensibility & Customization

### 8.1 Adding New Entity or Relation Types

1. Extend `EntityType` / `RelationType` enums in `src/config/legal_ontology.py`.
2. Update prompts and any hard‑coded logic in `graph_rag_indexer.py` to mention the new types.
3. If needed, add new parsers to `src/utils/legal_entity_parser.py` and integrate with `EntityResolver`.
4. Add tests under `tests/` and small examples in this document or the general README.

### 8.2 Custom Triple Validation

If you need stricter rules (e.g. disallow certain relation combinations):

- Implement additional checks in `Triple.normalize_and_validate()` or a post‑processing step.
- Use `flag_uncertain_triples` / human validation hooks to surface cases for review.

### 8.3 Alternative LLMs / Providers

The indexer uses the `OpenAI` Python client, but the overall interface is abstract enough that you can:

- Plug in different chat models (e.g. domain‑tuned models) by modifying the client wrapper
- Adjust token pricing/env vars without touching core logic

Ensure you preserve the JSON output contract expected by `Triple`.

---

## 9. Operational Guidelines

- Run indexing in **small batches** initially (`--max-chunks`) to validate ontology mappings.
- Keep APOC enabled in Neo4j for best performance with typed relationships and dynamic labels.
- Monitor vector index health regularly if you rely on Neo4j vector search.
- Prefer **canonical IDs** in all application‑level queries to avoid duplicate entity issues.

For a system‑wide performance view (including measured speed‑ups), cross‑check `docs/OPTIMIZATIONS.md`.
