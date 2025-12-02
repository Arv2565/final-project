# Legal RAG System Documentation

## Overview

This is a **Dual-Retrieval RAG System** for legal document processing combining:
1. **Vector Retrieval**: Qdrant + inLegalBERT (768-dim embeddings)
2. **Graph Retrieval**: Neo4j + GraphRAG (hierarchical legal knowledge)
3. **LangGraph Workflows**: Multi-step orchestration

## Quick Start

```bash
# Environment Setup
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Verify setup
python -c "from src.config.settings import validate_environment; print('✅ Ready!' if validate_environment() else '❌ Check config')"
```

## Core Workflows

### 1. Vector Ingestion (Qdrant)

**Process**: PDF/JSON → Text extraction → inLegalBERT embeddings → Qdrant storage

```bash
# Single document
python scripts/ingest_legal_documents.py --file document.pdf --court "Supreme Court"

# Batch directory
python scripts/ingest_legal_documents.py --directory data/knowledge_base/ --recursive

# Search
python scripts/ingest_legal_documents.py --search "contract breach" --limit 5

# Status
python scripts/ingest_legal_documents.py --status
```

**Configuration** (`.env`):
```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legal_documents

LEGAL_BERT_MODEL=nlpaueb/legal-bert-base-uncased
CHUNK_SIZE=450
CHUNK_OVERLAP=50
EMBEDDING_DEVICE=auto
```

### 2. Graph Ingestion (Neo4j + GraphRAG)

**Process**: Documents → LLM triple extraction → Legal ontology validation → Neo4j hierarchical graph

```bash
# Index with graph + embeddings
python scripts/graph_rag_index.py --paths data/knowledge_base/ --recursive

# Skip embeddings (faster)
python scripts/graph_rag_index.py --paths data/ --no-embed

# Test with limited chunks
python scripts/graph_rag_index.py --paths data/ --max-chunks 10
```

**Requirements**:
- OpenAI API key for triple extraction
- Neo4j with **APOC plugin** (required for hierarchical labels)
- Neo4j credentials in `.env`

**Configuration** (`.env`):
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=your_openai_key
OPENAI_CHAT_MODEL=gpt-4o-mini
```

## Architecture Deep Dive

### Legal Knowledge Graph (GraphRAG)

**Ontology**: 57 entity types + 80+ canonical relationships

**Entity Types**:
- `Legal_Act`, `Statute`, `Constitution`
- `Section`, `Clause`, `Chapter`, `Schedule`
- `Offence`, `Penalty`, `Right`, `Duty`
- `Court`, `Tribunal`, `Authority`
- `Definition`, `Procedure`, `Jurisdiction`

**Relationship Types**:
- Definitional: `defines`, `classifies`, `is_instance_of`
- Structural: `part_of`, `contains`, `section_in`, `chapter_in`
- Amendment: `amends`, `repeals`, `supersedes`, `replaces`
- Enforcement: `enforces`, `interprets`, `adjudicates`
- Citation: `cites`, `referenced_in`, `relies_on`
- Procedural: `procedure_for`, `prerequisite_to`, `precedes`

**Node Structure**:
```cypher
(:Entity:Section {
  name: "section_420",              // Normalized name
  display_name: "Section 420 IPC",  // Human-readable
  entity_type: "Section",           // Ontology type
  canonical_id: "IPC:Section:420",  // Unique identifier
  law_level: "statute",             // Document level
  source: "ipc.json",               // Origin file
  embedding: [...]                  // Optional vector
})
```

**Hierarchical Relationships**:
```cypher
(:Section)-[:PART_OF_HIERARCHY {
  relation_confidence: 1.0,
  inferred: false,
  source: "ipc.json"
}]->(:Chapter)-[:PART_OF_HIERARCHY]->(:Act)
```

### Triple Extraction Pipeline

1. **Document Context Detection**: Auto-detect IPC, Constitution, CPC, CrPC, etc.
2. **Domain-Aware Prompts**: 
   - System prompt with legal ontology (entity types + relations)
   - Few-shot examples from real legal documents
   - Document-specific guidance (e.g., "This is IPC - criminal law")
3. **LLM Extraction**: GPT-4o-mini extracts JSON triples with entity types
4. **Validation**: Pydantic validation + ontology normalization
5. **Confidence Scoring**: 1.0 (exact), 0.8 (alias), 0.5 (unknown)
6. **Neo4j Ingestion**: Dynamic label assignment via APOC + relationship creation

### Neo4j APOC Requirement

**Why APOC?** Cypher cannot dynamically add labels. APOC enables:
```cypher
CALL apoc.create.addLabels(node, ["Section"]) 
```

**Installation**:

**Neo4j Desktop**: Plugins tab → Install "APOC Core" → Restart

**Docker**:
```bash
# Download matching version from https://github.com/neo4j/apoc/releases
docker cp apoc-5.x.x-all.jar neo4j_container:/var/lib/neo4j/plugins/
docker restart neo4j_container
```

**Verify**:
```cypher
CALL apoc.version()
```

**Fallback (no APOC)**: Query by property instead of label:
```cypher
MATCH (s:Entity)-[:PART_OF_HIERARCHY]->(c:Entity)
WHERE s.entity_type = 'Section' AND c.entity_type = 'Chapter'
RETURN s.display_name, c.display_name
```

## Query Examples

### Vector Search (Qdrant)
```python
from src.workflows.legal_document_ingestion import get_ingestion_workflow

workflow = get_ingestion_workflow()
results = workflow.search_similar_documents(
    query_text="breach of contract damages",
    limit=10,
    filters={"court": "Supreme Court"}
)
```

### Graph Traversal (Neo4j)

**Find sections in chapters**:
```cypher
MATCH (s:Section)-[:PART_OF_HIERARCHY]->(c:Chapter)
RETURN s.display_name AS section, c.display_name AS chapter
LIMIT 10
```

**Full hierarchy traversal**:
```cypher
MATCH path = (s:Section)-[:PART_OF_HIERARCHY*..5]->()
WHERE s.canonical_id = 'IPC:Section:420'
RETURN path
```

**Semantic relations**:
```cypher
MATCH (a:Section)-[r:RELATION {type: 'amends'}]->(b:Section)
RETURN a.display_name, b.display_name, r.relation_confidence
```

**Low-confidence review**:
```cypher
MATCH (a)-[r:RELATION]->(b)
WHERE r.relation_confidence < 0.8
RETURN a.display_name, r.type, b.display_name, r.relation_confidence
ORDER BY r.relation_confidence ASC
```

### Hybrid Retrieval (Vector + Graph)
```python
from src.workflows.graphs.retrieval import vector_nearest_entities, expand_graph_seeds

# 1. Semantic search
seeds = vector_nearest_entities("Section 420 fraud", top_k=5)
entity_names = [name for name, score, meta in seeds]

# 2. Graph expansion
neighbors = expand_graph_seeds(entity_names, hops=2, limit_per_seed=10)
```

## System Configuration

### Environment Variables

**Core Database**:
```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legal_documents

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=required
```

**Embeddings**:
```bash
LEGAL_BERT_MODEL=nlpaueb/legal-bert-base-uncased
EMBEDDING_BATCH_SIZE=8
EMBEDDING_DEVICE=auto  # auto/cuda/cpu/mps
```

**Processing**:
```bash
CHUNK_SIZE=450
CHUNK_OVERLAP=50
```

**LLM (GraphRAG)**:
```bash
OPENAI_API_KEY=required
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_RATE_CHAT_INPUT_PER_1K=5.00
OPENAI_RATE_CHAT_OUTPUT_PER_1K=15.00
OPENAI_RATE_EMBED_PER_1K=0.13
```

**Production**:
```bash
APP_ENV=development
LOG_LEVEL=INFO
LOG_SENSITIVE_DATA=false
```

## Troubleshooting

### Connection Issues
```bash
# Test Qdrant
curl http://localhost:6333/collections

# Test Neo4j
cypher-shell -u neo4j -p password "RETURN 'connected'"

# Test APOC
cypher-shell -u neo4j -p password "CALL apoc.version()"
```

### Memory Issues
```bash
# Reduce batch sizes
export EMBEDDING_BATCH_SIZE=4
export EMBEDDING_DEVICE=cpu
```

### Model Loading
```bash
# Clear cache
rm -rf ~/.cache/huggingface/transformers/

# Test internet
ping huggingface.co
```

## Performance Optimization

### GPU Acceleration
- Set `EMBEDDING_DEVICE=cuda` for 5-10x faster embeddings
- Monitor GPU memory with `nvidia-smi`

### Batch Processing
- Qdrant: Increase `EMBEDDING_BATCH_SIZE` (8-32)
- GraphRAG: Use `--max-chunks` for testing before full runs

### Neo4j Indexing
```cypher
-- Index for hierarchical queries
CREATE INDEX section_canonical_id IF NOT EXISTS FOR (s:Section) ON (s.canonical_id)
CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)

-- Vector index (requires Neo4j 5.x+)
CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}}
```

## Project Structure

```
src/
├── agents/              # LangChain knowledge extractors
├── config/              # Settings, ontology, extraction examples
├── database/            # Qdrant, Neo4j, embedding services
├── processing/          # Document processors (PDF, JSON, TXT)
├── scrapers/            # Web scrapers for legal sources
├── workflows/           # Main orchestration workflows
│   └── graphs/          # GraphRAG indexing, retrieval, enrichment
└── utils/               # PDF extractors, helpers

scripts/                 # CLI entry points
├── ingest_legal_documents.py      # Qdrant ingestion
├── graph_rag_index.py             # Neo4j graph indexing
└── verify_hierarchy_setup.py     # System verification

docs/                    # Documentation
data/                    # Legal document storage
tests/                   # Unit and integration tests
```

## Common Workflows

### Adding New Document Types
1. Update `ProcessingConfig.supported_extensions`
2. Add extraction method in `DocumentProcessor`
3. Implement category inference logic
4. Update metadata schema

### Extending Ontology
1. Add entity types to `EntityType` enum in `legal_ontology.py`
2. Add relationships to `RelationType` enum
3. Update system prompts in `graph_rag_indexer.py`
4. Add examples to `legal_extraction_examples.json`

### Custom Queries
Combine vector + graph for powerful hybrid retrieval:
```python
# 1. Semantic: Find relevant entities
entities = vector_nearest_entities("fraud penalties IPC", top_k=10)

# 2. Graph: Expand to related concepts
for name, score, meta in entities:
    # Traverse hierarchy
    cypher = "MATCH (e:Entity {name: $name})-[:PART_OF_HIERARCHY*..3]->() RETURN ..."
    
    # Find citations
    cypher = "MATCH (e:Entity {name: $name})-[:RELATION {type: 'cites'}]->() RETURN ..."
```

## Status & Limitations

### ✅ Implemented
- Vector ingestion with inLegalBERT + Qdrant
- Graph ingestion with legal ontology + Neo4j
- 57 entity types, 80+ relation types
- Domain-aware triple extraction
- Confidence scoring and validation
- Hierarchical relationships via APOC
- Cost tracking for LLM/embedding usage

### ⚠️ Partial
- Hierarchical labels (requires APOC)
- Vector retrieval (Python-side cosine, not Neo4j native)
- Chunk nodes (chunks not stored as entities)

### ❌ Not Implemented
- Temporal versioning (amendments over time)
- Legal citation parsing (regex for "Section 420 IPC")
- Bidirectional relationships
- Human review UI for low-confidence triples
- Automated backfilling of missing hierarchies

## Development

### Testing
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Specific module
pytest tests/unit/test_enrichment.py -v
```

### Adding Features
1. Follow existing code patterns in `src/`
2. Add type hints to all functions
3. Use Google-style docstrings
4. Handle errors gracefully with logging
5. Add tests for new functionality

## References

- **inLegalBERT**: [nlpaueb/legal-bert-base-uncased](https://huggingface.co/nlpaueb/legal-bert-base-uncased)
- **Qdrant**: [qdrant.tech](https://qdrant.tech)
- **Neo4j APOC**: [neo4j.com/labs/apoc](https://neo4j.com/labs/apoc)
- **OpenAI Embeddings**: text-embedding-3-large (3072-dim)

## License

Production-ready legal tech application. Ensure compliance with your organization's data handling policies.
