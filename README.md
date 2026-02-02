# AI Legal Assistant - Full Stack Application

A comprehensive AI-powered legal assistance platform built with LangGraph and FastAPI.

## Architecture

This project follows a 3-tier architecture:

```
final-project/
├── frontend/     # Web UI (Coming Soon)
├── backend/      # FastAPI Gateway  
└── tool/         # AI Legal Assistant Core
```

### Components

- **Frontend** (`frontend/`): Modern web interface for user interactions
- **Backend** (`backend/`): REST/WebSocket API gateway handling authentication and routing
- **Tool** (`tool/`): LangGraph-based AI engine for legal query processing

## Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose (for Qdrant)
- Node.js 18+ (for frontend, when implemented)

### 1. Setup Tool (AI Engine)

```bash
cd tool
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys (GOOGLE_API_KEY required)
```

### 2. Start Qdrant Vector Database

From the root directory:

```bash
docker-compose up -d
```

Or from the tool directory:

```bash
cd tool
docker-compose -f docker-compose.langfuse.yml up -d
```

### 3. Setup Backend (API)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 4. Run Backend Server

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000/api
- Docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/health

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/api/health

# Chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the steps to file a bail application?"}'
```

### 6. Run Frontend (When Available)

```bash
cd frontend
npm install
npm run dev
```

## Development

### Running Individual Components

**Tool (Standalone)**:
```bash
cd tool
source venv/bin/activate
python app.py
```

**Backend (API Server)**:
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

**Frontend (When Implemented)**:
```bash
cd frontend
npm run dev
```

### Using Docker Compose

A `docker-compose.yml` file can orchestrate all services:

```bash
docker-compose up -d
```

## Project Structure

```
final-project/
├── frontend/                    # Web UI
│   └── README.md
├── backend/                     # API Gateway
│   ├── src/
│   │   ├── main.py             # FastAPI app
│   │   ├── routes/             # API endpoints
│   │   ├── services/           # Business logic
│   │   └── schemas/            # Request/response models
│   ├── requirements.txt
│   └── README.md
├── tool/                        # AI Legal Assistant Core
│   ├── src/
│   │   ├── agents/             # LangGraph agents
│   │   ├── workflows/          # Workflow builders
│   │   ├── models/             # State models
│   │   ├── prompts/            # Agent prompts
│   │   └── ...
│   ├── data/                   # Legal knowledge base
│   ├── pipelines/              # Data ingestion
│   ├── requirements.txt
│   └── README.md
├── docker-compose.yml          # Multi-service orchestration
└── README.md                   # This file
```

## Features

- **Procedural Guidance**: Step-by-step legal procedure instructions
- **Activity-to-Law Mapping**: Connect user activities to relevant legal sections
- **Evidence Linking**: Map facts to applicable laws
- **Document Generation**: Create legal documents from templates
- **Multi-Domain Support**: Civil (CPC) and Criminal (BNSS) law
- **Real-time Chat**: WebSocket support for streaming responses

## Documentation

See individual README files for detailed documentation:

- [Tool Documentation](tool/README.md) - AI engine setup and usage
- [Backend Documentation](backend/README.md) - API gateway setup and endpoints
- [Frontend Documentation](frontend/README.md) - Web UI (coming soon)

## API Documentation

Once the backend is running, access:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Legal Domain Coverage

### Criminal Law
- **BNSS**: Bharatiya Nagarik Suraksha Sanhita (Indian criminal procedure)
- Covers: Bail applications, arrests, FIRs, trials, appeals

### Civil Law
- **CPC**: Code of Civil Procedure  
- Covers: Divorce, property disputes, injunctions, suits

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation
- **WebSockets**: Real-time communication

### Tool (AI Engine)
- **LangGraph**: Agent workflow orchestration
- **Gemini**: Google's LLM for text generation
- **Qdrant**: Vector database for RAG
- **LangChain**: LLM framework utilities

### Frontend (Planned)
- **Next.js 14**: React framework
- **Tailwind CSS**: Styling
- **shadcn/ui**: UI components
- **React Query**: API state management

## Environment Variables

### Tool
```env
GOOGLE_API_KEY=your_gemini_api_key
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Backend
```env
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000
```

## Development Workflow

1. **Make changes to tool**: Edit agents, prompts, workflows in `tool/src/`
2. **Test tool standalone**: Run `python app.py` in tool directory
3. **Update backend**: Modify routes/services in `backend/src/` if needed
4. **Test API**: Use curl or API docs to test endpoints
5. **Update frontend**: Build UI components that call the API

## Troubleshooting

### Backend Can't Import Tool

Ensure the tool directory exists and is properly set up:

```bash
ls -la tool/src/workflows/chat/
```

The backend uses relative imports (`../tool`), so directory structure must be correct.

### Qdrant Connection Failed

Check if Qdrant is running:

```bash
docker ps | grep qdrant
curl http://localhost:6333
```

### Port Already in Use

Change the port in backend:

```bash
uvicorn src.main:app --reload --port 8001
```

## Contributing

1. Create a feature branch
2. Make changes in the appropriate directory (frontend/backend/tool)
3. Test thoroughly
4. Submit a pull request

## License

[Your License]

## Support

For issues or questions, please open a GitHub issue.
