# Legal Document Ingestion Workflow

## Overview

This document describes the streamlined workflow for storing legal documents in Qdrant using inLegalBERT for generating embeddings. The system is designed for clarity, modularity, and scalability while maintaining production-ready standards for legal data processing.

## Three-Step Process

The workflow follows a strict three-step process:

### 1. Extract and Preprocess Legal Documents
- **Input**: PDF or JSON files containing legal documents
- **Processing**: 
  - Text extraction using PyPDF2 (PDF) or JSON parsing
  - Text cleaning and normalization
  - Chunking for inLegalBERT's 512-token limit
  - Metadata extraction and standardization
- **Output**: List of `DocumentChunk` objects with text and metadata

### 2. Generate Dense Embeddings
- **Input**: Document chunks with text content
- **Processing**:
  - Load inLegalBERT model (`nlpaueb/legal-bert-base-uncased`)
  - Generate 768-dimensional embeddings
  - Handle batching for efficiency
  - Respect 512-token limit with truncation/padding
- **Output**: Embedding vectors paired with document chunks

### 3. Store in Qdrant Vector Database
- **Input**: Document chunks with their embeddings
- **Processing**:
  - Create Qdrant collection with proper configuration
  - Store embeddings with rich metadata
  - Create indexes for legal document fields
  - Generate unique point IDs
- **Output**: List of stored point IDs in Qdrant

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PDF/JSON      │    │   inLegalBERT    │    │     Qdrant      │
│   Documents     │───▶│   Embeddings     │───▶│   Vector DB     │
│                 │    │                  │    │                 │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • Text Extract  │    │ • 768-dim vectors│    │ • Similarity    │
│ • Chunking      │    │ • Batch process  │    │   Search        │
│ • Metadata      │    │ • 512-token limit│    │ • Metadata      │
│ • Cleaning      │    │ • GPU/CPU support│    │   Filtering     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Key Features

### Document Processing
- **Multi-format Support**: PDF and JSON input files
- **Intelligent Chunking**: Respects inLegalBERT's token limits with overlap
- **Metadata Extraction**: Automatically extracts and standardizes legal metadata
- **Text Cleaning**: Removes artifacts while preserving legal terminology

### Embedding Generation
- **inLegalBERT Integration**: Uses domain-specific legal language model
- **Efficient Batching**: Processes multiple chunks simultaneously
- **Device Management**: Automatic GPU/CPU/MPS device selection
- **Token Management**: Handles truncation and padding for 512-token limit

### Vector Storage
- **Qdrant Integration**: Production-ready vector database
- **Metadata Indexing**: Optimized for legal document filtering
- **Batch Operations**: Efficient storage of large document collections
- **Error Handling**: Robust error recovery and logging

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Core Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legal_documents

# Model Configuration
LEGAL_BERT_MODEL=nlpaueb/legal-bert-base-uncased
MAX_TOKEN_LENGTH=512
CHUNK_SIZE=450
CHUNK_OVERLAP=50

# Optional: Production Settings
QDRANT_API_KEY=your_api_key_here
LOG_LEVEL=INFO
APP_ENV=production
```

### Metadata Fields

The system supports the following legal document metadata fields:

| Field | Type | Indexed | Description |
|-------|------|---------|-------------|
| `court` | string | ✅ | Court name (e.g., "Supreme Court") |
| `date` | datetime | ✅ | Document date |
| `case_number` | string | ❌ | Case reference number |
| `case_type` | string | ✅ | Type of case (e.g., "Civil", "Criminal") |
| `jurisdiction` | string | ✅ | Legal jurisdiction |
| `title` | string | ❌ | Document title |
| `judges` | string | ❌ | Judge names |
| `parties` | string | ❌ | Case parties |
| `file_type` | string | ✅ | Original file type |
| `source_file` | string | ❌ | Source filename |

## Usage Examples

### Basic Document Ingestion

```python
from workflows.legal_document_ingestion import get_ingestion_workflow

# Initialize workflow
workflow = get_ingestion_workflow()

# Ingest a single document
result = workflow.ingest_single_document("judgment.pdf", {
    "court": "Supreme Court",
    "date": "2023-01-15",
    "case_type": "Civil"
})

print(f"Processed {result.chunks_created} chunks")
print(f"Stored {len(result.points_stored)} points")
```

### Batch Processing

```python
# Ingest multiple documents
files = ["doc1.pdf", "doc2.json", "doc3.pdf"]
metadata = [
    {"court": "High Court", "case_type": "Criminal"},
    {"court": "District Court", "case_type": "Civil"},
    {"court": "Supreme Court", "case_type": "Constitutional"}
]

result = workflow.ingest_documents(files, metadata)
print(f"Success: {result.successful_files}/{result.total_files}")
```

### Directory Processing

```python
# Process all documents in a directory
result = workflow.ingest_directory(
    directory_path="/path/to/legal/documents",
    recursive=True,
    file_pattern="*.pdf"
)
```

### Document Search

```python
# Search for similar documents
results = workflow.search_similar_documents(
    query_text="breach of contract damages",
    limit=10,
    filters={"court": "Supreme Court"}
)

for result in results:
    print(f"Score: {result['score']:.4f}")
    print(f"Source: {result['metadata']['source_file']}")
    print(f"Text: {result['text'][:200]}...")
```

## Command Line Usage

The system includes a comprehensive CLI script:

```bash
# Ingest a single document
python scripts/ingest_legal_documents.py \
    --file judgment.pdf \
    --court "Supreme Court" \
    --date "2023-01-15"

# Ingest a directory
python scripts/ingest_legal_documents.py \
    --directory /path/to/documents \
    --recursive

# Search documents
python scripts/ingest_legal_documents.py \
    --search "contract breach damages" \
    --limit 5 \
    --filter-court "Supreme Court"

# Check collection status
python scripts/ingest_legal_documents.py --status
```

## Performance Considerations

### Hardware Requirements
- **CPU**: Multi-core processor recommended for parallel processing
- **Memory**: 8GB+ RAM for model loading and document processing
- **GPU**: CUDA-compatible GPU recommended for faster embedding generation
- **Storage**: SSD recommended for database performance

### Scalability
- **Batch Size**: Adjust `EMBEDDING_BATCH_SIZE` based on available memory
- **Chunk Size**: Balance between context preservation and processing speed
- **Parallel Processing**: System supports concurrent document processing

### Optimization Tips
1. **GPU Acceleration**: Use CUDA-enabled GPU for 5-10x faster embedding generation
2. **Batch Processing**: Process multiple documents together for better efficiency
3. **Memory Management**: Monitor memory usage with large document collections
4. **Qdrant Tuning**: Optimize Qdrant configuration for your use case

## Security and Compliance

### Data Protection
- **Environment Variables**: Sensitive configuration stored in `.env` files
- **API Keys**: Secure storage and transmission of API credentials
- **Audit Logging**: Comprehensive logging for compliance tracking
- **Data Retention**: Configurable retention policies

### Legal Compliance
- **Data Privacy**: No sensitive document content logged by default
- **Access Control**: Integrate with existing authentication systems
- **Audit Trail**: Complete processing history maintained
- **Data Encryption**: Optional encryption for sensitive data

## Troubleshooting

### Common Issues

1. **Connection Errors**
   ```bash
   # Check Qdrant connectivity
   curl http://localhost:6333/collections
   
   # Verify environment configuration
   python -c "from config.settings import validate_environment; print(validate_environment())"
   ```

2. **Memory Issues**
   ```bash
   # Reduce batch size
   export EMBEDDING_BATCH_SIZE=4
   
   # Use CPU if GPU memory insufficient
   export EMBEDDING_DEVICE=cpu
   ```

3. **Model Loading Errors**
   ```bash
   # Clear model cache
   rm -rf ~/.cache/huggingface/transformers/
   
   # Verify internet connectivity for model download
   ping huggingface.co
   ```

### Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| ENV_001 | Environment validation failed | Check `.env` configuration |
| DB_001 | Qdrant connection failed | Verify Qdrant service is running |
| MODEL_001 | inLegalBERT loading failed | Check internet connection and disk space |
| PROC_001 | Document processing failed | Verify file format and permissions |

## API Reference

### Core Classes

- **`LegalDocumentIngestionWorkflow`**: Main orchestrator class
- **`DocumentProcessor`**: Handles PDF/JSON processing and chunking
- **`InLegalBERTEmbeddingService`**: Manages embedding generation
- **`QdrantLegalDocumentStore`**: Handles vector database operations

### Data Models

- **`DocumentChunk`**: Represents processed document segments
- **`IngestionResult`**: Contains batch processing results
- **`EmbeddingResult`**: Contains embedding generation results

See the inline documentation in each module for detailed API information.

## Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure
4. Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`
5. Run tests: `pytest tests/`

### Code Standards

- **Type Hints**: All functions must include type annotations
- **Docstrings**: Google-style docstrings for all modules and functions
- **Error Handling**: Comprehensive exception handling and logging
- **Testing**: Unit and integration tests for all functionality

## License

This legal document ingestion workflow is designed for production use in legal technology applications. Ensure compliance with your organization's data handling policies and applicable regulations.