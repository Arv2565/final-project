import logging
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Initialize logging FIRST
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
logger.info(f"Loading env from: {env_path}")
load_dotenv(env_path)

import os
llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
logger.info(f"LLM Provider: {llm_provider}")

if llm_provider == "gemini":
    if os.getenv("GEMINI_API_KEY"):
        logger.info("GEMINI_API_KEY found.")
    else:
        logger.error("GEMINI_API_KEY NOT found!")
else:
    if os.getenv("OPENAI_API_KEY"):
        logger.info("OPENAI_API_KEY found.")
    else:
        logger.error("OPENAI_API_KEY NOT found!")

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.api.socket_handler import handle_websocket_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up Legal AI Assistant API...")
    yield
    # Shutdown logic
    logger.info("Shutting down Legal AI Assistant API...")

app = FastAPI(
    title="Legal AI Assistant API",
    description="FastAPI backend for the Dual-Retrieval RAG System with WebSocket support.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Legal AI Assistant"}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket_connection(websocket)

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
