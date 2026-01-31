
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure src is in path
sys.path.append(str(Path.cwd()))

# Load env exactly like app.py
load_dotenv(Path.cwd() / ".env")

from src.config import get_llm_config
from src.agents.agent_llm_helper import get_agent_llm
from src.models import OrchestratorPlan

def test_exact():
    print("Testing with exact project configuration...")
    try:
        llm = get_agent_llm(model_type="writer", output_schema=OrchestratorPlan)
        print(f"LLM initialized: {llm}")
        # Invoke
        print("Invoking...")
        # Since it is a writer agent with output schema, we need to provide messages that match expected input or just a string
        # actually for structure output it might expect messages. 
        # But let's just send a simple string, langchain usually handles it.
        result = llm.invoke("Hello")
        print("Success:", result)
    except Exception as e:
        print(f"Caught expected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_exact()
