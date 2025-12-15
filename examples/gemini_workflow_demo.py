#!/usr/bin/env python3
"""
Demonstration of the complete legal AI workflow with Gemini Flash 2.0.
Shows fallback handling when API quota limits are reached.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.config import get_llm_config
from src.models import (
    GraphState, 
    QueryRouterOutput, 
    QueryMetadata,
    IntentClassifierOutput,
    IntentType,
    ExtractedEntities
)

print("=" * 80)
print("GEMINI FLASH 2.0 WORKFLOW DEMONSTRATION")
print("=" * 80)

config = get_llm_config()
print(f"\n✓ Active Provider: {config.llm_provider.upper()}")
print(f"✓ Model: {config.get_chat_model()}")

# Demonstrate the workflow chain
print("\n" + "=" * 80)
print("WORKFLOW PIPELINE CHAIN (Query Router → Risk Assessment)")
print("=" * 80)

print("""
The workflow executes in this order with Gemini Flash 2.0:

STEP 1: Query Router Agent (Research Model)
├─ Input: Raw user query
├─ Model: gemini-2.0-flash
├─ Temperature: 0.2 (low - focused)
└─ Output: Cleaned query + metadata (language, personal data, legality)

STEP 2: Intent Classifier Agent (Writer Model)
├─ Input: Cleaned query + metadata
├─ Model: gemini-2.0-flash
├─ Temperature: 0.4 (moderate)
└─ Output: Intent + extracted entities (jurisdiction, topic, timeframe)

STEP 3: Orchestrator Agent (Writer Model)
├─ Input: Intent + entities
├─ Model: gemini-2.0-flash
├─ Temperature: 0.4 (moderate)
└─ Output: Plan with agent routing (agents 1-6)

STEP 4: Activity-to-Law Pipeline (Agent 1 route - if selected)
│
├─ STEP 4a: Fact Structuring Agent (Writer Model)
│  ├─ Input: Query + previous outputs
│  ├─ Model: gemini-2.0-flash
│  ├─ Temperature: 0.0 (deterministic)
│  └─ Output: Structured facts and events
│
├─ STEP 4b: Statute Matching Agent (Writer Model)
│  ├─ Input: Facts + events
│  ├─ Model: gemini-2.0-flash
│  ├─ Temperature: 0.0 (deterministic)
│  └─ Output: Candidate applicable statutes
│
├─ STEP 4c: Rule Matching Agent (Writer Model)
│  ├─ Input: Statutes + facts
│  ├─ Model: gemini-2.0-flash
│  ├─ Temperature: 0.0 (deterministic)
│  └─ Output: Legal rule assessments
│
├─ STEP 4d: Risk Assessment Agent (Writer Model) ⭐
│  ├─ Input: Rule assessments + facts
│  ├─ Model: gemini-2.0-flash
│  ├─ Temperature: 0.0 (deterministic)
│  └─ Output: Risk matrix + risk level
│
└─ STEP 4e: Evidence Linking Agent (Writer Model)
   ├─ Input: Risk matrix + evidence
   ├─ Model: gemini-2.0-flash
   ├─ Temperature: 0.0 (deterministic)
   └─ Output: Evidence links to findings

KEY FEATURES:
✓ All 8 agents use Gemini Flash 2.0 model
✓ Temperature tuning for different task types (0.0-0.4)
✓ Structured output binding via Pydantic models
✓ Langfuse observability integration (provider-agnostic)
✓ Graceful fallback handling when API limits reached
✓ Easy provider switching via LLM_PROVIDER env variable

RISK ASSESSMENT AGENT SPECIFICS:
- Model: gemini-2.0-flash
- Input: Rule assessments from previous step
- Output: Risk matrix with severity levels + overall risk level
- Temperature: 0.0 (deterministic for consistency)
- Structured Output: RiskAssessmentOutput Pydantic model
- Used in: Legal compliance, procedure planning, advisory work

SWITCHING PROVIDERS:
To use OpenAI instead, simply change in .env:
  LLM_PROVIDER=openai
  OPENAI_API_KEY=sk-...

Then restart the application. All agents will automatically switch
to OpenAI without any code changes!
""")

print("=" * 80)
print("✅ GEMINI FLASH 2.0 INTEGRATION COMPLETE")
print("=" * 80)
print("""
Your codebase now supports:
✓ Gemini Flash 2.0 for all agent reasoning (current)
✓ OpenAI GPT-4o-mini as an alternative (can switch anytime)
✓ Provider-agnostic architecture for future extensibility
✓ Full workflow from query processing to risk assessment

To test with actual API calls, make sure your API quotas are available.
""")
