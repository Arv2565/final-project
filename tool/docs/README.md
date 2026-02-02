# Legal RAG System (Vector + GraphRAG)

This repository implements a production-ready **dual retrieval** legal RAG system that combines:

- **Vector retrieval** over chunks using inLegalBERT + Qdrant / Neo4j vector indexes
- **GraphRAG** over a rich Neo4j legal knowledge graph
- **LangChain / LangGraph-style workflows** for ingestion and query orchestration

The goal of this README is to be the **single entry point** for understanding, setting up, and operating the system. For a deeper technical view of the graph pipeline, see `GRAPH_RAG_FEATURES_AND_IMPLEMENTATION.md`.

---

## 1. High‑Level Architecture

### Components

- **Document processing** (`src/processing/`, `src/utils/pdf_extractor.py`)
  - Normalizes PDF / JSON / TXT sources into clean text + metadata
- **Vector store** (`scripts/ingest_legal_documents.py`, Qdrant / Neo4j vector index)
  - inLegalBERT embeddings (768‑dim) for semantic search over chunks
- **Legal knowledge graph (GraphRAG)** (`src/workflows/graphs/`)
  - 50+ entity types and 90+ typed relationships in Neo4j
  - Entity resolution and canonical IDs (e.g. `IPC:Section:420`)
- **LLM extraction** (`src/workflows/graphs/graph_rag_indexer.py`)
  - GPT‑4o‑mini extracts (head, relation, tail) triples with ontology‑aware prompts
- **Retrieval workflows** (`src/workflows/graphs/retrieval.py`)
  - Pure vector search, pure graph traversal, or hybrid (vector → graph expansion)

### Data Flow

1. **Ingestion → Vector**: documents → chunks → embeddings → Qdrant / Neo4j vector index
2. **Ingestion → GraphRAG**: documents → triples → canonical entities + typed edges → Neo4j graph
3. **Retrieval**: user query → embedding/vector search → seed entities → graph expansion → answer

---

## 2. Setup (One‑Time)

### 2.1 Prerequisites

- Python **3.9+**
- Docker (recommended for Qdrant, optional for Neo4j)
- Neo4j **5.x** with **APOC Core** plugin (for full GraphRAG features)

### 2.2 Install Python Dependencies

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials and local settings
```

### 2.3 Required Environment Variables (Minimal)

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
EMBEDDING_DEVICE=auto      # auto/cuda/cpu/mps
CHUNK_SIZE=450
CHUNK_OVERLAP=50

# GraphRAG LLM
OPENAI_API_KEY=your_openai_key
OPENAI_CHAT_MODEL=gpt-4o-mini

# Langfuse Observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000

# Optional cost tracking (defaults are sane)
OPENAI_RATE_CHAT_INPUT_PER_1K=5.00
OPENAI_RATE_CHAT_OUTPUT_PER_1K=15.00
OPENAI_RATE_EMBED_PER_1K=0.13
```

### 2.4 Start Services

**1. Qdrant (Vector Database)**
```bash
docker pull qdrant/qdrant
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

**2. Neo4j (Graph Database)**
```bash
docker pull neo4j:5.21.0
docker run -d \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_PLUGINS='["apoc"]' \
    neo4j:5.21.0
```

**3. Langfuse (Observability)**
```bash
# Clone the official repository
git clone https://github.com/langfuse/langfuse.git
cd langfuse

# Start via Docker Compose
docker compose up -d
```
*   Access Langfuse at: [http://localhost:3000](http://localhost:3000)
*   Create an account to get your generic `PUBLIC_KEY` and `SECRET_KEY`.

**4. Verify Environment**
```bash
python -c "from src.config.settings import validate_environment; print('✅ Ready!' if validate_environment() else '❌ Check config')"
```

For more Neo4j/APOC options and vector index tuning, see the GraphRAG doc.

---

## 3. Core Workflows

### 3.1 Vector Ingestion & Search (Qdrant)

**Ingest legal documents into Qdrant:**

```bash
# Single document
python scripts/ingest_legal_documents.py --file document.pdf --court "Supreme Court"

# Batch directory
python scripts/ingest_legal_documents.py --directory data/knowledge_base/ --recursive

# Status
python scripts/ingest_legal_documents.py --status
```

**Semantic search over stored documents:**

```bash
python scripts/ingest_legal_documents.py --search "contract breach" --limit 5
```

Programmatic example:

```python
from src.workflows.legal_document_ingestion import get_ingestion_workflow

workflow = get_ingestion_workflow()
results = workflow.search_similar_documents(
    query_text="breach of contract damages",
    limit=10,
    filters={"court": "Supreme Court"},
)
```

---

### 3.2 Graph Ingestion (Neo4j + GraphRAG)

The graph indexer turns documents into a hierarchical legal knowledge graph with canonical entities and typed relationships.

**Basic graph indexing:**

```bash
# Full graph + embeddings
python scripts/graph_rag_index.py --paths data/knowledge_base/ --recursive

# Faster iteration: no embeddings
python scripts/graph_rag_index.py --paths data/ --no-embed

# Safe dry‑run / small subset
python scripts/graph_rag_index.py --paths data/ --max-chunks 10
```

High‑level pipeline (see `GRAPH_RAG_FEATURES_AND_IMPLEMENTATION.md` for details):

1. Load and flatten JSON / PDF into text blocks
2. Chunk text and send to OpenAI chat model
3. Parse triples into `Triple` Pydantic model
4. Normalize entity/relationship types using `LegalOntology`
5. Resolve entities to canonical IDs via `EntityResolver`
6. Ingest nodes and typed relationships into Neo4j (APOC‑powered)
7. Optionally embed entities and update Neo4j vector index

---

### 3.3 Hybrid Retrieval (Vector + Graph)

Use vector search to find seed entities, then expand through the graph:

```python
from src.workflows.graphs.retrieval import (
    vector_nearest_entities,
    expand_graph_seeds,
)

# 1. Semantic seed search
seeds = vector_nearest_entities("Section 420 fraud", top_k=5)
entity_names = [name for name, score, meta in seeds]

# 2. Graph expansion around seeds
neighbors = expand_graph_seeds(
    entity_names,
    hops=2,
    relation_types=["CITES", "AMENDS"],
    limit_per_seed=10,
)
```

---

## 4. Graph & Vector Optimizations (Summary)

The system includes three major optimizations (see `OPTIMIZATIONS.md` for full metrics and details; Graph‑specific aspects are also summarized in the GraphRAG doc):

1. **Entity resolution** (`docs/ENTITY_RESOLUTION.md`, `src/utils/entity_resolver.py`)
   - Legal‑specific parsers for sections, cases, statutes
   - Canonical IDs like `IPC:Section:420`, `AIR_1970_SC_1876`
   - ~90% duplicate reduction and 5–10× faster traversals

2. **Typed relationships** (`docs/TYPED_RELATIONSHIPS_GUIDE.md`, `src/config/legal_ontology.py`)
   - 90+ canonical relation types mapped to Neo4j labels (`:AMENDS`, `:CITES`, ...)
   - 12–17× faster relationship queries vs a generic `:RELATION {type: ...}` model

3. **Native vector search** (`docs/VECTOR_SEARCH_OPTIMIZATION.md`, `scripts/vector_index_manager.py`)
   - Neo4j 5 vector index instead of Python‑side cosine similarity
   - 15–300× faster semantic search with O(log n) behaviour

---

## 5. Project Layout

```text
src/
├── agents/                # QueryRouter, IntentClassifier, and Knowledge Extractor
├── config/                # Settings, legal ontology, extraction examples
├── database/              # Qdrant + Neo4j clients, embedding services
├── processing/            # Document processors (PDF, JSON, TXT)
├── scrapers/              # Web scrapers for legal sources
├── workflows/             # Orchestration workflows (vector + graph)
│   ├── chat/              # LangGraph chat workflow (Router -> Intent Classifier)
│   └── graphs/            # GraphRAG indexing, enrichment, retrieval
└── utils/                 # PDF extraction, helpers

pipelines/                 # Ingestion and indexing pipelines (CLI)
├── cli/                   # CLI entrypoints
├── document_ingestion/    # Document processing
├── graph_index/           # GraphRAG indexing
└── vector_index/          # Vector index management

docs/
├── DOCUMENTATION_INDEX.md           # History of previous consolidations
├── OPTIMIZATIONS.md                 # Detailed performance work
├── ENTITY_RESOLUTION.md             # Entity resolution reference
├── TYPED_RELATIONSHIPS_GUIDE.md     # All relationship types
├── VECTOR_SEARCH_OPTIMIZATION.md    # Vector index deep‑dive
├── LEGAL_KNOWLEDGE_EXTRACTOR.md     # LangChain legal extractor
└── GRAPH_RAG_FEATURES_AND_IMPLEMENTATION.md  # GraphRAG design (this repo’s main graph doc)

tests/                               # Unit + integration tests
```

---

## 6. Query-Time Chat Workflow

The system uses a **LangGraph** workflow to process user queries:

1.  **Query Router Agent**: Normalizes the query, translates if necessary, and extracts basic metadata.
2.  **Intent Classifier Agent**: Classifies the user's intent (e.g., procedure, law explanation, case law) and extracts specific legal entities.

**Running the Chat Workflow:**

```bash
python src/app.py --question "What are the penalties under Section 420 IPC?"
```

---

## 7. Troubleshooting (Essentials)

**Connectivity**

```bash
# Qdrant
curl http://localhost:6333/collections

# Neo4j
cypher-shell -u neo4j -p password "RETURN 'connected'"

# APOC
cypher-shell -u neo4j -p password "CALL apoc.version()"
```

**Performance / memory issues**

- Reduce batch sizes:
  - `export EMBEDDING_BATCH_SIZE=4`
  - `export EMBEDDING_DEVICE=cpu`
- For Neo4j vector search, ensure `entity_embedding_index` is ONLINE using `pipelines/cli/vector_index_manager.py`.

**Model / cache issues**

```bash
rm -rf ~/.cache/huggingface/transformers/
```

---

## 8. Development & Testing

Run tests:

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Focused module
pytest tests/unit/test_enrichment.py -v
```

Contribution guidelines (informal):

1. Follow existing code patterns and type hints in `src/`
2. Use clear docstrings and structured logging
3. Preserve separation of concerns (processing vs graph vs vector vs UI)
4. Add tests and, where relevant, short documentation updates to this README or the GraphRAG doc

---

## 9. Related References

- **GraphRAG design & pipeline**: `docs/GRAPH_RAG_FEATURES_AND_IMPLEMENTATION.md`
- **Optimization details**: `docs/OPTIMIZATIONS.md`
- **Entity resolution**: `docs/ENTITY_RESOLUTION.md`
- **Typed relationships**: `docs/TYPED_RELATIONSHIPS_GUIDE.md`
- **Vector search tuning**: `docs/VECTOR_SEARCH_OPTIMIZATION.md`
- **Legal Knowledge Extractor**: `docs/LEGAL_KNOWLEDGE_EXTRACTOR.md`

External:

- inLegalBERT — https://huggingface.co/nlpaueb/legal-bert-base-uncased
- Qdrant — https://qdrant.tech
- Neo4j APOC — https://neo4j.com/labs/apoc
- Neo4j Vector Search — https://neo4j.com/docs/neo4j-manual/latest/query-tuning/vector-search/
