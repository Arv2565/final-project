# Legal Assistant Backend API

FastAPI gateway that exposes REST and WebSocket endpoints for the AI Legal Assistant tool.

## Overview

This backend serves as the API layer between the frontend and the AI legal assistant core (`tool/`). It handles:
- Request validation and routing
- Session management
- WebSocket connections for real-time chat
- API documentation via Swagger/ReDoc

## Setup

### 1. Create Virtual Environment

```bash
cd backend
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
# Edit .env as needed
```

### 4. Ensure Tool is Available

The backend imports from `../tool/`, so make sure the tool directory is properly set up:

```bash
cd ../tool
pip install -r requirements.txt
cp .env.example .env
# Configure tool .env with API keys
```

## Running the Server

### Development Mode

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## API Endpoints

### Health Check

```bash
GET /api/health
```

Returns server status and version information.

### Chat (REST)

```bash
POST /api/chat
Content-Type: application/json

{
  "query": "What are the steps to file a divorce petition?",
  "session_id": "optional-session-id"
}
```

### Chat (WebSocket)

```javascript
ws://localhost:8000/api/ws/chat

// Send message
{
  "query": "Your legal question here",
  "session_id": "optional-session-id"
}

// Receive responses
{
  "type": "status" | "response" | "error",
  "data": {...}
}
```

## Project Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app
│   ├── routes/              # API endpoints
│   │   ├── chat.py         # Chat endpoints
│   │   └── health.py       # Health check
│   ├── services/            # Business logic
│   │   └── chat_service.py # Tool integration
│   └── schemas/             # Pydantic models
│       └── chat.py         # Request/response schemas
├── requirements.txt
├── .env.example
└── README.md
```

## Development

### Adding New Endpoints

1. Create route in `src/routes/`
2. Add business logic in `src/services/`
3. Define schemas in `src/schemas/`
4. Register router in `src/main.py`

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is a bail application?"}'
```

## Deployment

For production deployment:

1. Set `DEBUG=false` in `.env`
2. Use production WSGI server (e.g., gunicorn)
3. Configure proper CORS origins
4. Set up SSL/TLS certificates
5. Use environment-specific configuration

## Troubleshooting

### Import Errors

If you get import errors from the tool:

```python
# Check tool path
import sys
from pathlib import Path
tool_path = Path(__file__).parent.parent.parent / "tool"
print(f"Tool path: {tool_path}")
print(f"Exists: {tool_path.exists()}")
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000
# Kill the process if needed
kill -9 <PID>
```
