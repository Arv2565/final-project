# AI Legal Assistant - Core Tool

LangGraph-based AI engine for legal query processing and guidance. This is the core intelligence layer used by the backend API.

## Overview

This tool provides comprehensive legal assistance through:
- **Procedural Guidance**: Step-by-step instructions for legal procedures (CPC & BNSS)
- **Activity-to-Law Mapping**: Linking user activities to relevant legal sections
- **Evidence Linking**: Connecting facts to applicable laws
- **Document Generation**: Creating legal documents based on templates

## Architecture

Built with LangGraph, the tool uses a multi-agent workflow:
- **Orchestrator Agent**: Routes queries to appropriate modules
- **Procedural Agents**: Generate procedural checklists, timelines, and guidance
- **Fact Structuring**: Extract and structure legal facts from queries
- **Response Generation**: Format and present results to users

## Setup

### 1. Create Virtual Environment

```bash
cd tool
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required: Gemini API key
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Langfuse for tracing
LANGFUSE_SECRET_KEY=your_key
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 4. Start Qdrant (Vector Database)

```bash
docker-compose -f docker-compose.langfuse.yml up -d
```

Or use the root-level docker-compose.yml if available.

## Usage

### Standalone CLI Mode

Run the tool directly from the command line:

```bash
python app.py
```

This will start an interactive chat session.

### As a Library (Backend Integration)

The backend imports this tool's components:

```python
import sys
sys.path.append('../tool')

from src.workflows.chat.builder import create_workflow
from src.models.state import GraphState

# Create workflow
workflow = create_workflow()

# Process query
initial_state = GraphState(user_query="Your legal question")
result = await workflow.ainvoke(initial_state)
```

## Project Structure

```
tool/
├── src/
│   ├── agents/          # LangGraph agents
│   ├── workflows/       # Workflow builders
│   ├── models/          # Pydantic state models
│   ├── prompts/         # Agent prompts
│   ├── nodes/           # Graph nodes
│   ├── retrieval/       # RAG components
│   ├── processing/      # Document processing
│   ├── database/        # Database utilities
│   └── config/          # Configuration
├── data/
│   ├── knowledge_base/  # Legal documents
│   ├── processed/       # Processed documents
│   └── templates/       # Document templates
├── pipelines/           # Data ingestion pipelines
├── scripts/             # Utility scripts
├── tests/               # Unit tests
├── examples/            # Example scripts
└── qdrant_storage/      # Vector DB storage
```

## Data Ingestion

To ingest legal documents into the knowledge base:

```bash
# Ingest all documents
python -m pipelines.ingest_all

# Or specific document types
python -m pipelines.legal_ingestion
```

## Running Tests

```bash
pytest tests/
```

## Examples

See `examples/` directory for usage examples:

```bash
# Demo procedural guidance
python examples/procedural_guidance_demo.py

# Test orchestration
python examples/demo_orchestration.py
```

## How It's Used

This tool is imported and used by:
- **Backend API** (`../backend/`): Exposes tool via REST/WebSocket
- **Standalone Scripts**: Direct CLI usage for testing
- **Data Pipelines**: Ingestion and processing workflows

## Legal Domain Coverage

### Criminal Law
- **BNSS (Bharatiya Nagarik Suraksha Sanhita)**: Criminal procedure code
- Focus on bail applications, arrests, trials, etc.

### Civil Law  
- **CPC (Code of Civil Procedure)**: Civil procedure code
- Focus on divorce, property disputes, injunctions, etc.

## Development

### Adding New Agents

1. Create agent in `src/agents/`
2. Define prompts in `src/prompts/`
3. Add node in `src/nodes/`
4. Update workflow in `src/workflows/`

### Modifying Prompts

All prompts are in `src/prompts/`. Edit the relevant files:
- Civil prompts: `CIVIL_*_SYSTEM_PROMPT`
- Criminal prompts: `CRIMINAL_*_SYSTEM_PROMPT`

## Troubleshooting

### Import Errors

Make sure you're in the tool directory and virtual environment is activated:

```bash
cd tool
source venv/bin/activate
python -c "from src.workflows.chat.builder import create_workflow; print('OK')"
```

### Qdrant Connection Issues

Check if Qdrant is running:

```bash
curl http://localhost:6333
```

### API Key Issues

Verify your `.env` file has the correct API keys:

```bash
cat .env | grep GOOGLE_API_KEY
```

## License

[Your License]
