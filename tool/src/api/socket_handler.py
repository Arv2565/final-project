import json
import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
from src.workflows.chat import build_graph, GraphState
from src.config.observability import get_langfuse_callback, setup_observability
from langfuse import get_client

# Ensure observability is set up
setup_observability()

logger = logging.getLogger(__name__)

async def handle_websocket_connection(websocket: WebSocket):
    await websocket.accept()
    
    session_id = str(uuid.uuid4())
    logger.info(f"New WebSocket session: {session_id}")
    
    # Initialize LangFuse client for this session
    langfuse_client = None
    try:
        langfuse_client = get_client()
    except Exception:
        pass

    # Initialize graph
    graph = build_graph()
    
    # Session state
    current_state: GraphState = {}
    clarification_count = 0
    MAX_CLARIFICATIONS = 5
    iteration = 0
    
    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            payload = message.get("payload")
            
            if msg_type == "query":
                # Initial query
                current_state = {
                    "user_query": str(payload).strip() if payload is not None else "",
                    "previous_user_message": current_state.get("previous_user_message", ""),
                    "previous_agent_message": current_state.get("previous_agent_message", ""),
                }
                clarification_count = 0
                iteration = 0
                await websocket.send_json({"type": "status", "payload": "Analyzing query..."})
                
            elif msg_type == "clarification_response":
                # Handle user response to clarification
                user_answer = payload
                
                # Retrieve the last clarification request from state (or we assume the flow is sequential)
                # In the 'app.py' logic, we had to re-construct the state.
                # Here, 'current_state' is preserved in this function scope.
                
                # Check if we have a pending clarification to resolve
                if current_state.get("pending_clarification"):
                    clarification = current_state["pending_clarification"]
                    
                    # Update history
                    history = current_state.get("clarification_history", [])
                    history.append({
                        "question": clarification['question'],
                        "answer": user_answer
                    })
                    
                    # Prepare state for next iteration
                    # Clear pending flag and orchestrator plan to force re-evaluation
                    new_state = {
                        "user_query": str(user_answer).strip(),
                        "router_output": current_state.get("router_output"),
                        "clarification_history": history,
                        "clarification_counts": current_state.get("clarification_counts", {}),
                        "previous_user_message": current_state.get("previous_user_message", ""),
                        "previous_agent_message": current_state.get("previous_agent_message", ""),
                    }
                    
                    # Preserve other non-volatile state
                    for key in current_state:
                        if key not in ["pending_clarification", "orchestrator_plan", "user_query", "router_output", "clarification_history", "clarification_counts", "previous_user_message", "previous_agent_message"]:
                            new_state[key] = current_state[key]
                            
                    current_state = new_state
                    await websocket.send_json({"type": "status", "payload": "Processing clarification..."})
                else:
                    await websocket.send_json({"type": "error", "payload": "No pending clarification found."})
                    continue
            else:
                await websocket.send_json({"type": "error", "payload": f"Unknown message type: {msg_type}"})
                continue

            # Run the Graph Loop (until result or next clarification)
            while True:
                iteration += 1
                
                # Setup callback
                callback_handler = get_langfuse_callback()
                config = {"callbacks": [callback_handler]} if callback_handler else {}
                
                if callback_handler:
                    callback_handler.session_id = session_id
                    callback_handler.metadata = {
                        "iteration": iteration,
                        "clarification_count": clarification_count, 
                        "has_clarification_history": bool(current_state.get("clarification_history"))
                    }

                # Node name mapping for user-friendly messages
                NODE_STATUS_MESSAGES = {
                    "query_router": "Analyzing your query...",
                    "orchestrator": "Understanding your legal needs...",
                    "fact_structuring": "Structuring the facts...",
                    "statute_matching": "Finding relevant laws...",
                    "rule_matching": "Matching legal rules...",
                    "risk_assessment": "Assessing legal implications...",
                    "evidence_linking": "Linking evidence to law...",
                    "response_generation": "Preparing your response...",
                    "procedural_guidance_civil": "Preparing civil procedure guidance...",
                    "procedural_guidance_criminal": "Preparing criminal procedure guidance...",
                    "timeline_constraint": "Identifying deadlines...",
                    "checklist_generator": "Creating document checklist...",
                    "responsible_actor": "Mapping responsible parties...",
                    "estimated_effort": "Estimating time and cost...",
                    "procedural_response": "Formatting procedural guidance...",
                    "case_retriever": "Retrieving relevant case law...",
                    "doc_gen_template_selection": "Selecting the right legal template...",
                    "doc_gen_placeholder_extraction": "Extracting required document details...",
                    "doc_gen_clarification": "Checking for missing information...",
                    "doc_gen_document_creation": "Drafting your legal document...",
                    "doc_gen_procedure_generation": "Adding filing and procedure guidance...",
                    "general_chat": "Preparing response...",
                }

                try:
                    final_state = None
                    
                    # Use streaming to capture node events
                    async for event in graph.astream_events(current_state, config=config, version="v2"):
                        kind = event.get("event")
                        name = event.get("name", "")
                        
                        # Send status update when a node starts
                        if kind == "on_chain_start" and name in NODE_STATUS_MESSAGES:
                            status_msg = NODE_STATUS_MESSAGES[name]
                            await websocket.send_json({"type": "status", "payload": status_msg})
                        
                        # Capture the final state
                        if kind == "on_chain_end" and name == "LangGraph":
                            final_state = event.get("data", {}).get("output", {})
                    
                    # Fallback if streaming didn't capture state
                    if not final_state:
                        final_state = await graph.ainvoke(current_state, config=config)
                        
                except Exception as e:
                    logger.error(f"Graph execution failed: {e}")
                    # Fallback to sync invoke
                    final_state = graph.invoke(current_state, config=config)
                
                # Check for clarification
                if final_state.get("pending_clarification"):
                    clarification_count += 1
                    
                    if clarification_count > MAX_CLARIFICATIONS:
                         await websocket.send_json({"type": "status", "payload": "Max clarifications reached. Proceeding..."})
                         # Clear pending and loop again
                         current_state = {**final_state}
                         if "pending_clarification" in current_state:
                             del current_state["pending_clarification"]
                         if "orchestrator_plan" in current_state:
                             del current_state["orchestrator_plan"]
                         continue

                    # Send clarification request to client
                    clarification = final_state["pending_clarification"]
                    # Update current_state so we have it for the next user response
                    current_state = final_state 
                    
                    response_payload = {
                        "question": clarification['question'],
                        "reason": clarification.get('reason'),
                        "options": clarification.get('options')
                    }
                    await websocket.send_json({"type": "clarification_request", "payload": response_payload})
                    
                    # Flush callbacks
                    if langfuse_client:
                        try:
                            langfuse_client.flush()
                        except: pass
                        
                    # Break inner loop to wait for user input
                    break
                
                # If no clarification, we have a result!
                router_output = final_state.get("router_output")
                final_response = final_state.get("final_response")
                case_retriever_markdown = final_state.get("case_retriever_markdown")
                case_pdf_paths = final_state.get("case_pdf_paths", [])

                logger.debug(f"Socket handler state: final_response={bool(final_response)}, case_markdown={bool(case_retriever_markdown)}, pdfs={len(case_pdf_paths)}")

                # Send case markdown if available from case retrieval
                if case_retriever_markdown and isinstance(case_retriever_markdown, str) and case_retriever_markdown.strip():
                    await websocket.send_json({"type": "case_markdown", "payload": case_retriever_markdown})
                    logger.info(f"Sent case retriever markdown output: {len(case_retriever_markdown)} chars")
                
                # Send case_pdf_paths if available from case retrieval
                if case_pdf_paths and isinstance(case_pdf_paths, list) and len(case_pdf_paths) > 0:
                    await websocket.send_json({"type": "case_pdfs", "payload": case_pdf_paths})
                    logger.info(f"Sent {len(case_pdf_paths)} case PDF paths")
                
                # Check for procedural guidance state - could be civil, criminal, or generic
                procedural_state = (
                    final_state.get("procedural_guidance_civil_state") or 
                    final_state.get("procedural_guidance_criminal_state") or
                    final_state.get("procedural_guidance_state")
                )
                
                activity_state = final_state.get("activity_law_state")
                
                result_payload = {}
                payload_source = "unknown"
                
                if final_response:
                    result_payload["text"] = final_response
                    final_state["previous_user_message"] = current_state.get("user_query", "")
                    final_state["previous_agent_message"] = final_response
                    payload_source = "final_response"
                    logger.info(f"Result payload populated from final_response")
                elif case_retriever_markdown and isinstance(case_retriever_markdown, str) and case_retriever_markdown.strip():
                    result_payload["text"] = case_retriever_markdown
                    final_state["previous_user_message"] = current_state.get("user_query", "")
                    final_state["previous_agent_message"] = case_retriever_markdown
                    payload_source = "case_retriever_markdown"
                    logger.info(f"Result payload populated from case_retriever_markdown: {len(case_retriever_markdown)} chars")
                    
                elif procedural_state:
                    result_payload["workflow"] = "procedural"
                    
                    # Convert Pydantic model to dict
                    if isinstance(procedural_state, dict):
                        proc_dict = procedural_state
                    else:
                        # Use model_dump() for Pydantic v2 or dict() for v1
                        proc_dict = procedural_state.model_dump() if hasattr(procedural_state, 'model_dump') else procedural_state.dict()
                    
                    # Extract sub-components
                    result_data = {}
                    
                    if proc_dict.get("timeline_constraints"):
                        tc = proc_dict["timeline_constraints"]
                        result_data["timeline_constraints"] = tc.get("constraints", []) if isinstance(tc, dict) else []
                    
                    if proc_dict.get("checklist"):
                        cl = proc_dict["checklist"]
                        result_data["checklist"] = cl.get("items", []) if isinstance(cl, dict) else []
                    
                    if proc_dict.get("actor_mapping"):
                        am = proc_dict["actor_mapping"]
                        result_data["actor_mapping"] = am.get("actor_mappings", []) if isinstance(am, dict) else []
                    
                    if proc_dict.get("estimated_effort"):
                        ee = proc_dict["estimated_effort"]
                        if isinstance(ee, dict):
                            result_data["estimated_effort"] = {
                                "ordered_steps": ee.get("ordered_steps", []),
                                "total_estimated_time": ee.get("total_estimated_time", ""),
                                "total_estimated_cost": ee.get("total_estimated_cost", "")
                            }
                    
                    result_payload["data"] = result_data
                    
                elif activity_state:
                    result_payload["workflow"] = "activity_law"
                    
                    # Convert activity state
                    if isinstance(activity_state, dict):
                        act_dict = activity_state
                    else:
                        act_dict = activity_state.model_dump() if hasattr(activity_state, 'model_dump') else activity_state.dict()
                    
                    result_data = {}
                    if act_dict.get("fact_structuring"):
                        fs = act_dict["fact_structuring"]
                        result_data["factors"] = fs.get("factors", []) if isinstance(fs, dict) else []
                        result_data["events"] = fs.get("events", []) if isinstance(fs, dict) else []
                    
                    result_payload["data"] = result_data

                
                # CRITICAL: Ensure result_payload has content - fallback to case_retriever_markdown if empty
                if not result_payload and case_retriever_markdown and isinstance(case_retriever_markdown, str) and case_retriever_markdown.strip():
                    logger.warning(f"Result payload was empty but case_retriever_markdown available ({len(case_retriever_markdown)} chars) - using as fallback")
                    result_payload["text"] = case_retriever_markdown
                    payload_source = "case_retriever_markdown_fallback"
                
                # Final fallback if still empty
                if not result_payload:
                    logger.warning("Result payload is still empty - adding generic fallback status")
                    result_payload = {"text": "Query processed. No results to display."}
                    payload_source = "fallback_generic"
                
                logger.info(f"Sending final_result with payload from: {payload_source}")
                await websocket.send_json({"type": "final_result", "payload": result_payload})

                # Persist updated state for next user message in this session
                current_state = final_state
                
                # Flush callbacks
                if langfuse_client:
                    try:
                        langfuse_client.flush()
                    except: pass
                
                # Wait for next query (break inner loop, return to outer loop)
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket session disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
        try:
           await websocket.send_json({"type": "error", "payload": str(e)})
        except:
           pass

