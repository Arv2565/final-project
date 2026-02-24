import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Import models using relative imports
from .models.user import User
from .models.session import Session
from .models.chat import Message, ChatHistory

async def init_db():
    """
    Initialize MongoDB connection and Beanie ODM.
    Call this function on FastAPI startup, similar to mongoose.connect().
    """
    # Use environment variable or default local URI
    mongo_uri = os.getenv("MONGOURI", "mongodb://localhost:27017/Dike")
    
    # Create Motor asynchronous client
    client = AsyncIOMotorClient(mongo_uri)
    
    # Extract database name from URI
    db_name = client.get_database().name if client.get_database().name else "legal_assistant"
    
    # Initialize Beanie with the loaded document models
    await init_beanie(
        database=client[db_name],
        document_models=[
            User,
            Session,
            Message,
            ChatHistory
        ]
    )
    print(f"Connected to MongoDB database: {db_name}")
