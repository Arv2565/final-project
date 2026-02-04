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

from .routes import chat, health

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
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Legal Assistant API Gateway starting up...")
    logger.info("API Documentation available at: http://localhost:8000/api/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Legal Assistant API Gateway shutting down...")
