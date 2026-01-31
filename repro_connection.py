
import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in env")
        return

    print(f"Testing with API Key: {api_key[:5]}...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        api_key=api_key,
    )
    
    try:
        print("Attempting to invoke LLM...")
        result = await llm.ainvoke("Hello, are you there?")
        print("Success!")
        print(result.content)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
