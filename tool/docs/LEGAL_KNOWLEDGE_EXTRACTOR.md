# Legal Knowledge Extractor

A LangChain-powered agent that extracts structured knowledge from legal PDF documents using OpenAI's GPT models and Pydantic for data validation.

## Features

- **Structured Extraction**: Extracts title, purpose, scope, key provisions, and administration details
- **Pydantic Validation**: Ensures consistent data structure with proper typing
- **PDF Processing**: Handles PDF text extraction with cleaning and preprocessing
- **Batch Processing**: Process entire directories of PDF files
- **Error Handling**: Comprehensive error handling and logging
- **JSON Output**: Saves results in structured JSON format

## Components

### 1. Pydantic Model (`src/models/legal_document.py`)
Defines the structure for extracted legal knowledge:
- `title`: Document title
- `purpose`: Purpose or objective
- `scope`: Applicability scope  
- `key_provisions`: 4-6 key operational provisions
- `administration`: Administration/enforcement details

### 2. PDF Extractor (`src/utils/pdf_extractor.py`)
Handles PDF text extraction with:
- Multi-page processing
- Text cleaning and formatting
- Metadata extraction
- Error recovery

### 3. LangChain Agent (`src/agents/legal_knowledge_extractor.py`)
The main extraction agent featuring:
- Custom output parser for structured data
- GPT-3.5-turbo-instruct model
- Exact prompt matching user specifications
- Batch and single-file processing

## Usage

### Command Line Interface

```bash
# Process all PDFs in central acts folder (auto-detected)
python scripts/extract_legal_knowledge.py

# Process specific directory
python scripts/extract_legal_knowledge.py --directory data/knowledge_base/central_acts/

# Process single file
python scripts/extract_legal_knowledge.py --file data/knowledge_base/constitution_of_india.pdf

# Custom output file
python scripts/extract_legal_knowledge.py --output my_extraction.json

# Enable debug logging
python scripts/extract_legal_knowledge.py --log-level DEBUG
```

### Programmatic Usage

```python
from pathlib import Path
from src.agents.legal_knowledge_extractor import LegalDocumentKnowledgeExtractor

# Initialize extractor
extractor = LegalDocumentKnowledgeExtractor()

# Process single PDF
pdf_path = Path("data/knowledge_base/constitution_of_india.pdf")
knowledge = extractor.extract_from_pdf(pdf_path)

# Process directory
results = extractor.extract_from_directory(Path("data/central_acts/"))

# Save results
extractor.save_results_to_json(results, Path("output.json"))
```

## Setup Requirements

### Environment Variables
```bash
# Required: OpenAI API Key
export OPENAI_API_KEY='your-api-key-here'
```

### Dependencies
Install required packages:
```bash
pip install langchain>=0.0.350 langchain-openai>=0.0.5 pydantic>=2.0.0 PyPDF2>=3.0.0
```

## Output Format

The extractor produces JSON with this exact structure:

```json
{
  "source_file": "/path/to/document.pdf",
  "file_name": "document.pdf",
  "title": "Document Title",
  "purpose": "Document purpose...",
  "scope": "Document scope...", 
  "key_provisions": [
    "Section 1: First key provision",
    "Section 2: Second key provision",
    "Section 3: Third key provision",
    "Section 4: Fourth key provision"
  ],
  "administration": "Administrative details..."
}
```

## Extraction Rules

The agent follows these strict rules:
1. **Source-only**: Derive content only from PDF, no external knowledge
2. **Precision**: Preserve legal meaning without paraphrasing  
3. **Completeness**: If information unavailable, use "information not publicly available"
4. **Structure**: Exactly 4-6 key provisions with section/rule numbers
5. **Procedures**: Identify specific procedures, forms, timelines, committees
6. **Quotes**: Preserve verbatim quotes from original document
7. **Translation**: Indicate translated fields with "(translated)" suffix

## Graph RAG Ingestion

The system ingests triples into Neo4j using **native typed relationships** for optimal query performance:

### Triple Extraction

Extracted from legal documents as structured (head, relation, tail) triples:
```python
Triple(
    head="Section 420, IPC",
    relation="penalizes",
    tail="Cheating",
    head_type="Section",
    tail_type="Offence",
    relation_confidence=0.95
)
```

### Typed Relationship Creation

Each triple is ingested with a **native Neo4j relationship type** based on the relation:

- **Before (Anti-pattern)**: `(section)-[r:RELATION {type: "penalizes"}]->(offence)`
- **After (Best Practice)**: `(section)-[r:PENALIZES]->(offence)`

**Benefits:**
- 15-20x faster queries
- Native Neo4j type indexing
- Semantically clear relationship labels
- Better query optimization

### Supported Relationship Types

92 canonical relation types mapped to Neo4j labels:
- Structural: `PART_OF`, `CONTAINS`, `SECTION_IN`, etc.
- Amendment: `AMENDS`, `REPEALS`, `MODIFIES`, etc.
- Reference: `CITES`, `REFERENCES`, `RELIES_ON`, etc.
- Enforcement: `ENFORCES`, `IMPLEMENTS`, `INTERPRETS`, etc.

See **TYPED_RELATIONSHIPS_GUIDE.md** for complete reference.

### Query Examples

Find all judgments citing a section:
```cypher
MATCH (section)-[r:CITED_IN]->(judgment)
WHERE section.name CONTAINS "420"
RETURN judgment, r.relation_confidence
```

Find provisions modified by amendments:
```cypher
MATCH (amendment)-[r:AMENDS]->(original)
RETURN amendment, original, r.created_at
```

Traverse the statutory hierarchy:
```cypher
MATCH (act)-[r:CONTAINS*1..3]->(section)
RETURN section, length(r) as depth
```

## File Structure

```
src/
├── agents/
│   └── legal_knowledge_extractor.py  # Main LangChain agent
├── models/  
│   └── legal_document.py            # Pydantic model
└── utils/
    └── pdf_extractor.py             # PDF processing utility

scripts/
└── extract_legal_knowledge.py      # CLI interface

examples/
└── legal_extraction_example.py     # Usage example
```

## Error Handling

- **PDF Extraction Failures**: Logs errors, continues with other files
- **API Failures**: Graceful fallback with "information not publicly available"
- **Parsing Errors**: Returns valid fallback structure
- **File Not Found**: Clear error messages with suggested fixes
- **Token Limits**: Automatic content truncation for large PDFs

## Logging

Comprehensive logging to both console and file:
- `INFO`: Processing status and summaries
- `DEBUG`: Detailed extraction steps  
- `WARNING`: Non-fatal issues (truncation, parsing failures)
- `ERROR`: Fatal errors requiring attention

## Testing

Run the example to test your setup:
```bash
python examples/legal_extraction_example.py
```

This will process the first PDF found in your data directory and show the extracted knowledge.

## Integration with Existing System

The legal knowledge extractor integrates with your existing RAG system:
- Uses same PDF processing patterns as document ingestion
- Compatible with existing metadata schemas
- Follows project logging and error handling conventions
- Can be integrated into workflows for enhanced document understanding