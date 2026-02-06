from typing import Dict, Any, List
import logging
from src.models import GraphState
from src.models.document_generation import DocumentGenerationState, TemplateInfo, PlaceholderInfo
from src.agents.document_generation.template_selection_agent import TemplateSelectionAgent
from src.agents.document_generation.placeholder_extraction_agent import PlaceholderExtractionAgent
from src.agents.document_generation.document_generation_agent import DocumentGenerationAgent
from src.agents.document_generation.procedure_generation_agent import ProcedureGenerationAgent
from src.prompts.document_generation_prompts import QUESTION_GENERATION_SYSTEM_PROMPT
from src.agents.agent_llm_helper import get_agent_llm

# Initialize agents
template_selection_agent = TemplateSelectionAgent()
placeholder_extraction_agent = PlaceholderExtractionAgent()
document_generation_agent_instance = DocumentGenerationAgent()
procedure_generation_agent = ProcedureGenerationAgent()

def document_generation_node(state: GraphState) -> Dict[str, Any]:
    """
    Main entry point for document generation workflow.
    Handles the state machine logic:
    1. Select Template
    2. Extract Placeholders
    3. Request User Input (Pause)
    4. Generate Document & Procedure
    """
    print("---DOCUMENT GENERATION NODE---")
    
    # Initialize state if missing
    doc_state = state.get("document_generation_state", {})
    if not doc_state:
        doc_state = {
            "status": "selecting_template",
            "selected_template": None,
            "placeholders": [],
            "user_inputs": {},
            "generated_document": None,
            "generated_procedure": None
        }
    
    # --- PHASE 1: TEMPLATE SELECTION ---
    if doc_state["status"] == "selecting_template":
        query = state.get("user_query")
        # You might also want to look at router_output or orchestrator_plan for context
        
        print("Selecting template...")
        selected_template = template_selection_agent(query)
        doc_state["selected_template"] = selected_template
        doc_state["status"] = "extracting_placeholders"
        
        # We can fall through to next step immediately
        
    # --- PHASE 2: PLACEHOLDER EXTRACTION ---
    if doc_state["status"] == "extracting_placeholders":
        template_info: TemplateInfo = doc_state["selected_template"]
        if not template_info:
             # Should not happen unless selection failed
             raise ValueError("No template selected")
             
        print(f"Extracting placeholders from {template_info.template_file}...")
        placeholders = placeholder_extraction_agent(template_info.template_file)
        doc_state["placeholders"] = placeholders
        
        # Check if we have any placeholders. If none, we could skip input.
        if not placeholders:
            doc_state["status"] = "generating"
        else:
            doc_state["status"] = "waiting_for_input"
            
            # --- PHASE 3: PREPARE USER INPUT REQUEST (INTERRUPT) ---
            # We need to construct a clarification request to be sent to user
            
            # Generate a friendly question using LLM
            question_generator_llm = get_agent_llm(model_type="writer") # Use writer or standard model
            
            p_keys = [p.key for p in placeholders]
            
            q_system_prompt = QUESTION_GENERATION_SYSTEM_PROMPT
            q_user_prompt = f"Document Name: {template_info.name}\nRequired Details: {p_keys}"
            
            try:
                question_text = question_generator_llm.invoke([
                    {"role": "system", "content": q_system_prompt},
                    {"role": "user", "content": q_user_prompt}
                ]).content
            except Exception as e:
                logging.error(f"Failed to generate question: {e}")
                question_text = f"I found the '{template_info.name}' template. Please describe the agreement and provide the necessary details in your own words."
            
            # We use the 'pending_clarification' mechanism to pause execution
            # The 'clarification' object usually has: question, reason, options
            pending_clarification = {
                "question": question_text,
                "reason": "Missing document details",
                "options": [] # Text input
            }
            
            # IMPORTANT: We return here to let the graph pause/interrupt
            # The main loop (app.py or socket_handler) handles 'pending_clarification'
            return {
                "document_generation_state": doc_state,
                "pending_clarification": pending_clarification
            }

    # --- PHASE 3 (Resume): HANDLE USER INPUT ---
    # If we are here and status is 'waiting_for_input', it means we MIGHT have received input
    # HOWEVER, the standard clarification loop in `chat_service.py` appends to `clarification_history`.
    # We need to check if we just returned from a user response.
    
    if doc_state["status"] == "waiting_for_input":
        # Check clarification history for the answer
        history = state.get("clarification_history", [])
        if not history:
            # We shouldn't be here without history if we requested clarification earlier.
            # Unless this is the first pass, which is handled above.
            # If we are effectively re-entering this node, it might be due to a graph cycle.
            pass
        else:
            last_interaction = history[-1]
            user_response = last_interaction.get("answer", "")
            
            print(f"Received user input: {user_response}")
            
            # We no longer parse into a dictionary. We pass the raw user response to the agent.
            doc_state["user_inputs"] = user_response # Store raw text
            doc_state["status"] = "generating"

    # --- PHASE 4: GENERATION ---
    if doc_state["status"] == "generating":
        print("Generating documents...")
        template_info = doc_state["selected_template"]
        placeholders_list = [p.dict() for p in doc_state["placeholders"]] # Pydantic to dict
        # 1. Document
        # Agent now accepts (template_file, placeholders_list, user_response_string)
        user_response = doc_state.get("user_inputs", "")
        generated_doc = document_generation_agent_instance.generate(
            template_info.template_file,
            placeholders_list,
            user_response
        )
        doc_state["generated_document"] = generated_doc
        
        # 2. Procedure
        generated_proc = procedure_generation_agent(
            template_info.procedure_file,
            template_info.name
        )
        doc_state["generated_procedure"] = generated_proc
        
        doc_state["status"] = "completed"
        
        # Set final fields for graph output
        return {
            "document_generation_state": doc_state,
            "final_response": f"I have generated the {template_info.name} for you.",
            "generated_document_content": generated_doc,
             # We might want to save to a specific path or return content
        }

    return {"document_generation_state": doc_state}
