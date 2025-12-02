# Setup Guide

This guide consolidates all setup and quick-start instructions for the Legal RAG system, including APOC installation, environment configuration, and first ingestion.

## 1. Prerequisites

- Python 3.9+
- Docker (recommended for Qdrant and optionally Neo4j)
- Neo4j 5.x with APOC Core plugin for full graph features

## 2. Install Dependencies

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
```

### Required environment variables

```bash
# Vector DB (Qdrant)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legal_documents

# Graph DB (Neo4j)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Embeddings
LEGAL_BERT_MODEL=nlpaueb/legal-bert-base-uncased
EMBEDDING_DEVICE=auto  # auto/cuda/cpu/mps

# GraphRAG LLM (for triple extraction)
OPENAI_API_KEY=your_openai_key
OPENAI_CHAT_MODEL=gpt-4o-mini

# Processing
CHUNK_SIZE=450
CHUNK_OVERLAP=50
```

## 3. Start Services

### Qdrant (Vector DB)
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Neo4j with APOC (recommended options)

Option A: Prebuilt image with APOC
```bash
docker run -d \
  --name neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4JLABS_PLUGINS='["apoc"]' \
  neo4j:5.21-enterprise
```

Option B: Add APOC manually to an existing container
```bash
# Find a matching release at https://github.com/neo4j/apoc/releases
wget https://github.com/neo4j/apoc/releases/download/5.21.0/apoc-5.21.0-all.jar
docker cp apoc-5.21.0-all.jar neo4j:/var/lib/neo4j/plugins/
docker restart neo4j
```

Verify APOC
```cypher
CALL apoc.version()
```

If APOC is not available, the system still works with property-based queries but without dynamic labels.

## 4. Verify Environment

```bash
python -c "from src.config.settings import validate_environment; print('✅ Ready!' if validate_environment() else '❌ Check config')"
```

## 5. First Ingestion and Search

### Vector ingestion (Qdrant)
```bash
# Single document
python scripts/ingest_legal_documents.py --file document.pdf --court "Supreme Court"

# Batch directory
python scripts/ingest_legal_documents.py --directory data/knowledge_base/ --recursive

# Search stored documents
python scripts/ingest_legal_documents.py --search "contract breach" --limit 5

# Status
python scripts/ingest_legal_documents.py --status
```

### Graph indexing (Neo4j + GraphRAG)
```bash
# Index graph with embeddings
python scripts/graph_rag_index.py --paths data/knowledge_base/ --recursive

# Faster iteration (skip embeddings)
python scripts/graph_rag_index.py --paths data/ --no-embed

# Limit chunks for test runs
python scripts/graph_rag_index.py --paths data/ --max-chunks 10
```

## 6. Vector Index for Neo4j (Optional but recommended)

Create and validate a Neo4j native vector index for O(log n) ANN search.
```bash
# Create index
python scripts/vector_index_manager.py create

# Check status
python scripts/vector_index_manager.py status

# Validate and get stats
python scripts/vector_index_manager.py validate
python scripts/vector_index_manager.py stats
```

## 7. Common Queries

```cypher
-- Sections in chapters
MATCH (s:Section)-[:PART_OF_HIERARCHY]->(c:Chapter)
RETURN s.display_name, c.display_name
LIMIT 10;

-- Full hierarchy traversal
MATCH p=(s:Section)-[:PART_OF_HIERARCHY*..5]->() 
WHERE s.canonical_id='IPC:Section:420'
RETURN p;
```

## 8. Troubleshooting

- APOC not found
```cypher
CALL apoc.version()  // If not found, (re)install APOC and restart Neo4j
```

- Nodes missing labels (APOC unavailable)
```cypher
MATCH (s:Entity)-[:PART_OF_HIERARCHY]->(c:Entity)
WHERE s.entity_type='Section' AND c.entity_type='Chapter'
RETURN s, c;
```

- Qdrant connectivity
```bash
curl http://localhost:6333/collections
```

- Model cache issues
```bash
rm -rf ~/.cache/huggingface/transformers/
```

- Memory pressure during embedding
```bash
export EMBEDDING_BATCH_SIZE=4
export EMBEDDING_DEVICE=cpu
```

## 9. File Map (Quick Reference)

- `scripts/ingest_legal_documents.py` — Vector ingestion/search
- `scripts/graph_rag_index.py` — Graph indexing
- `scripts/vector_index_manager.py` — Neo4j vector index management
- `src/config/legal_ontology.py` — Entity/relation types
- `src/workflows/graphs/graph_rag_indexer.py` — Ingestion to Neo4j
- `src/workflows/graphs/retrieval.py` — Hybrid retrieval
