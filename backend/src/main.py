"""Main FastAPI application for Legal Assistant API Gateway."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST, before any imports that depend on them
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Add tool to sys.path BEFORE importing any services that use it
tool_path = Path(__file__).parent.parent.parent / "tool"
if str(tool_path) not in sys.path:
    sys.path.insert(0, str(tool_path))

from .routes import chat, health, auth, user, chat_history, files
from .db import init_db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Legal Assistant API",
    description="API Gateway for AI Legal Assistant - Routes requests to the LangGraph-based tool",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(chat_history.router, prefix="/api/chat-history", tags=["chat-history"])
app.include_router(files.router, prefix="/api", tags=["files"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Legal Assistant API Gateway starting up...")
    await init_db()
    logger.info("API Documentation available at: http://localhost:8000/api/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Legal Assistant API Gateway shutting down...")
