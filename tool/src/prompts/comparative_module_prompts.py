from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
COMPARE_INDEX_PATH = WORKSPACE_ROOT / "tool" / "data" / "compare" / "compare_index.json"

EMPTY_QUERY_MESSAGE = "Please provide a comparison query with topic and two states."

CLARIFICATION_REASON = "Comparative module requires two explicit states for accurate mapping."
CLARIFICATION_QUESTION_SINGLE_STATE = "You mentioned {state}. Which second state should I compare it with?"
CLARIFICATION_QUESTION_NO_STATES = "Which two states should I compare for this legal topic?"

PRECOMPUTED_INTRO_TEMPLATE = "Using an existing comparison table for {topic} between {state_1} and {state_2}."
PRECOMPUTED_CONCLUSION_TEMPLATE = (
    "In summary, the pre-mapped table shows material differences between {state_1} and {state_2} "
    "for {topic}."
)

FALLBACK_INTRO_TEMPLATE = (
    "No precomputed comparison table was mapped for this exact query, so this response was synthesized "
    "from state-wise legal findings for {state_1} and {state_2}."
)
FALLBACK_CONCLUSION_TEMPLATE = (
    "In conclusion, the comparison highlights key differences between {state_1} and {state_2}. "
    "For production use, this fallback should be augmented with deeper statute retrieval for query-specific sections."
)

FALLBACK_NO_MATCH_ROWS = [
    {
        "aspect": "Legal dataset availability",
        "value": "No directly mapped comparison file found for {state} on this topic.",
    },
    {
        "aspect": "Suggested next step",
        "value": "Run statute-level retrieval for this state to populate a query-specific comparison.",
    },
]

TABLE_NOT_FOUND_VALUE = "Not found"


COMPARATIVE_AGENT1_SYSTEM_PROMPT = """You are Comparative Agent 1: State and Topic Selector.
Extract up to two Indian state names from the query and infer the legal topic.
If fewer than two states are explicit, set needs_clarification=true and write a concise clarification question.
Return structured output exactly matching the ComparativeAgent1Output schema.
"""


COMPARATIVE_AGENT2_SYSTEM_PROMPT = """You are Comparative Agent 2: State-1 Findings Retriever.
Given the user query, target state, and optional source context, generate concise legal findings for that state.
Return 3-7 findings as aspect/value pairs and a short summary.
Return structured output exactly matching the ComparativeStateFindingsOutput schema.
"""


COMPARATIVE_AGENT3_SYSTEM_PROMPT = """You are Comparative Agent 3: State-2 Findings Retriever.
Given the user query, target state, and optional source context, generate concise legal findings for that state.
Return 3-7 findings as aspect/value pairs and a short summary.
Return structured output exactly matching the ComparativeStateFindingsOutput schema.
"""


COMPARATIVE_AGENT4_SYSTEM_PROMPT = """You are Comparative Agent 4: Final Synthesizer.
Given mode, states, topic, and either a precomputed table or state findings, produce:
1) intro paragraph
2) markdown comparison table
3) conclusion paragraph
Return structured markdown output exactly matching the ComparativeAgent4Output schema.
"""
