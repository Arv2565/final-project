from typing import Dict, Any
import logging
from src.agents.agent_llm_helper import get_agent_llm
from src.models import GraphState
from src.prompts.document_generation_prompts import QUESTION_GENERATION_SYSTEM_PROMPT

# Language code to full name mapping for responses
LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
}

def doc_gen_clarification_node(state: GraphState) -> Dict[str, Any]:
    """
    Step 3: Check if we need user input for placeholders.
    If input is missing, generate a clarification request in the user's original language.
    If input allows (or placeholders empty), proceed to generation.
    The document will be generated in English, but clarifications are in the user's language.
    """
    print("---DOC GEN: CLARIFICATION CHECK---")
    
    doc_state = state.get("document_generation_state", {})
    placeholders = doc_state.get("placeholders", [])
    template_info = doc_state.get("selected_template")
    
    # Extract original language from router output
    router_output = state.get("router_output")
    original_language_code = "en"  # Default
    if router_output and hasattr(router_output, 'metadata') and router_output.metadata:
        original_language_code = router_output.metadata.original_language or "en"
    
    # If no placeholders, we can skip directly to generation
    if not placeholders:
        return {
            "document_generation_state": {
                **doc_state,
                "status": "generating",
                "user_inputs": ""
            }
        }
        
    # Check clarification history for an answer
    # Since the app.py loop accumulates history for the *current* query processing,
    # any history implies we asked a question and got an answer.
    history = state.get("clarification_history", [])
    
    if history:
        # We have an answer
        last_interaction = history[-1]
        user_response = last_interaction.get("answer", "")
        print(f"Received user input: {user_response}")
        
        return {
            "document_generation_state": {
                **doc_state,
                "user_inputs": user_response,
                "status": "generating"
            }
        }
    
    # No history, meaning we haven't asked yet. Generate question in original language.
    response_language_name = LANGUAGE_MAP.get(original_language_code, "English")
    print(f"Preparing clarification request in {response_language_name} language...")
    
    # Generate a friendly question using LLM
    question_generator_llm = get_agent_llm(model_type="writer")
    
    # Handle Pydantic model or dict
    p_keys = []
    for p in placeholders:
        if isinstance(p, dict):
             p_keys.append(p.get('key'))
        else:
             p_keys.append(p.key)
    
    try:
        keys_str = ", ".join(p_keys)
    except Exception:
        keys_str = str(placeholders)
    
    q_system_prompt = QUESTION_GENERATION_SYSTEM_PROMPT
    q_user_prompt = f"""Document Name: {template_info.name}
Required Details: {keys_str}

IMPORTANT: Respond ONLY in {response_language_name} (language code: {original_language_code}).
Do NOT use English. All your output must be in {response_language_name}."""
    
    try:
        question_text = question_generator_llm.invoke([
            {"role": "system", "content": q_system_prompt},
            {"role": "user", "content": q_user_prompt}
        ]).content
    except Exception as e:
        logging.error(f"Failed to generate question: {e}")
        question_text = f"I found the '{template_info.name}' template. Please describe the agreement and provide the necessary details in your own words."
    
    pending_clarification = {
        "question": question_text,
        "reason": "Missing document details",
        "options": [] 
    }
    
    return {
        "document_generation_state": {
            **doc_state,
            "status": "waiting_for_input"
        },
        "pending_clarification": pending_clarification
    }
