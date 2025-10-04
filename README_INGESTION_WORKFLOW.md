# Legal Document Ingestion Workflow - Quick Start

🚀 **Streamlined three-step workflow for storing legal documents in Qdrant using inLegalBERT embeddings**

## ⚡ Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
# At minimum, configure:
# QDRANT_HOST=localhost
# QDRANT_PORT=6333

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Qdrant Database

```bash
# Using Docker (recommended)
docker run -p 6333:6333 qdrant/qdrant

# Or using Docker Compose
echo "version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - '6333:6333'" > docker-compose.yml
docker-compose up -d
```

### 3. Ingest Your First Document

```bash
# Single document
python scripts/ingest_legal_documents.py \
    --file data/knowledge_base/bail_application.docx \
    --court "District Court" \
    --case-type "Bail Application"

# Batch directory
python scripts/ingest_legal_documents.py \
    --directory data/knowledge_base/ \
    --recursive
```

### 4. Search Documents

```bash
# Search for similar content
python scripts/ingest_legal_documents.py \
    --search "bail application procedures" \
    --limit 5

# Check collection status
python scripts/ingest_legal_documents.py --status
```

## 📋 Three-Step Process

### Step 1: Document Processing
- ✅ **PDF & JSON Support**: Extract text from both formats
- ✅ **Smart Chunking**: Respects inLegalBERT's 512-token limit
- ✅ **Metadata Extraction**: Automatic legal document metadata
- ✅ **Text Cleaning**: Preserves legal terminology

### Step 2: Embedding Generation
- ✅ **inLegalBERT Model**: Domain-specific legal language model
- ✅ **768-Dimensional Vectors**: Rich semantic representation
- ✅ **Batch Processing**: Efficient GPU/CPU utilization
- ✅ **Auto Device Detection**: CUDA/MPS/CPU support

### Step 3: Vector Storage
- ✅ **Qdrant Integration**: Production-ready vector database
- ✅ **Metadata Indexing**: Fast filtering by court, date, case type
- ✅ **Similarity Search**: Semantic search with scoring
- ✅ **Batch Operations**: Efficient bulk storage

## 🏗️ Architecture

```
📄 Legal Documents (PDF/JSON)
    ↓
🔄 Document Processor
    ├─ Text extraction
    ├─ Chunking (450 words)
    └─ Metadata extraction
    ↓
🧠 inLegalBERT Embeddings
    ├─ nlpaueb/legal-bert-base-uncased
    ├─ 768-dimensional vectors
    └─ Batch processing
    ↓
🔍 Qdrant Vector Database
    ├─ Similarity search
    ├─ Metadata filtering
    └─ Production scaling
```

## 📊 Key Features

| Feature | Description |
|---------|-------------|
| **Multi-format** | PDF and JSON document support |
| **Legal Domain** | inLegalBERT specialized for legal text |
| **Production Ready** | Error handling, logging, monitoring |
| **Scalable** | Batch processing and GPU acceleration |
| **Searchable** | Semantic search with metadata filtering |
| **Configurable** | Environment-based configuration |

## 🔧 Configuration

Essential environment variables:

```bash
# Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legal_documents

# Model
LEGAL_BERT_MODEL=nlpaueb/legal-bert-base-uncased
CHUNK_SIZE=450
CHUNK_OVERLAP=50

# Performance (optional)
EMBEDDING_BATCH_SIZE=8
EMBEDDING_DEVICE=auto  # auto, cpu, cuda, mps
```

## 📚 Usage Examples

### Python API

```python
from workflows.legal_document_ingestion import get_ingestion_workflow

workflow = get_ingestion_workflow()

# Single document
result = workflow.ingest_single_document("judgment.pdf", {
    "court": "Supreme Court",
    "case_type": "Civil"
})

# Search
results = workflow.search_similar_documents(
    "breach of contract", 
    limit=10
)
```

### Command Line

```bash
# Ingest with metadata
python scripts/ingest_legal_documents.py \
    --file contract.pdf \
    --court "High Court" \
    --jurisdiction "New York" \
    --case-type "Commercial"

# Directory ingestion
python scripts/ingest_legal_documents.py \
    --directory /legal/documents \
    --pattern "*.pdf"

# Filtered search
python scripts/ingest_legal_documents.py \
    --search "intellectual property rights" \
    --filter-court "Federal Court" \
    --limit 3
```

## 🚦 Status Check

Verify your setup:

```bash
# Check collection status
python scripts/ingest_legal_documents.py --status

# Test environment
python -c "
from src.config.settings import validate_environment
print('✅ Ready!' if validate_environment() else '❌ Check config')
"
```

## 📈 Performance Tips

1. **GPU Acceleration**: 5-10x faster with CUDA GPU
2. **Batch Size**: Increase for more memory, decrease for less
3. **Chunk Size**: Balance between context and speed
4. **SSD Storage**: Faster database operations

## 🔍 Metadata Schema

| Field | Type | Indexed | Example |
|-------|------|---------|---------|
| `court` | string | ✅ | "Supreme Court" |
| `date` | datetime | ✅ | "2023-01-15" |
| `case_type` | string | ✅ | "Civil" |
| `jurisdiction` | string | ✅ | "Federal" |
| `case_number` | string | ❌ | "2023-CV-001" |

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant` |
| Model download fails | Check internet: `ping huggingface.co` |
| Out of memory | Reduce `EMBEDDING_BATCH_SIZE=4` |
| Slow processing | Use GPU: `EMBEDDING_DEVICE=cuda` |

## 📖 Full Documentation

- **Complete Guide**: [`docs/legal_document_ingestion.md`](docs/legal_document_ingestion.md)
- **API Reference**: See docstrings in source files
- **Configuration**: [`.env.example`](.env.example)

## 🏆 Production Ready

✅ **Error Handling**: Comprehensive exception management  
✅ **Logging**: Detailed audit trails  
✅ **Monitoring**: Collection statistics and health checks  
✅ **Security**: Environment-based sensitive data  
✅ **Scalability**: Batch processing and GPU support  
✅ **Compliance**: Legal data privacy considerations  

---

**Get started in 5 minutes!** Perfect for legal tech applications requiring semantic document search and retrieval.