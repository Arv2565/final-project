"""Chat service that interfaces with the AI tool."""

import sys
import importlib
import importlib.util
from pathlib import Path
import logging
from typing import Optional, Dict, Any
from fastapi import WebSocket
import json

logger = logging.getLogger(__name__)


async def _extract_last_turn_context(chat_history) -> str:
    """Extract last user and assistant messages from persisted chat history and format as chat_context.
    
    Returns:
        Formatted chat_context string, or empty string if no context available.
    """
    if not chat_history or not getattr(chat_history, "messages", None):
        return ""

    previous_user_message = ""
    previous_agent_message = ""

    try:
        for message in reversed(chat_history.messages):
            resolved_message = message

            if not hasattr(resolved_message, "sender") or not hasattr(resolved_message, "content"):
                fetch_method = getattr(message, "fetch", None)
                if callable(fetch_method):
                    try:
                        resolved_message = await fetch_method()
                    except Exception:
                        resolved_message = message

            sender = (getattr(resolved_message, "sender", "") or "").lower()
            content = (getattr(resolved_message, "content", "") or "").strip()
            if not content:
                continue

            if not previous_agent_message and sender == "assistant":
                previous_agent_message = content
            elif not previous_user_message and sender == "user":
                previous_user_message = content

            if previous_user_message and previous_agent_message:
                break
    except Exception as e:
        logger.warning(f"Failed to derive previous turn context from chat history: {e}")
        return ""

    # Format as single chat_context string
    if previous_user_message and previous_agent_message:
        return f"Previous exchange:\nUser: {previous_user_message}\nAssistant: {previous_agent_message}"
    elif previous_user_message:
        return f"Previous user message: {previous_user_message}"
    elif previous_agent_message:
        return f"Previous assistant message: {previous_agent_message}"
    
    return ""

class ChatService:
    """Service for handling chat interactions with the AI legal assistant tool."""
    
    def __init__(self):
        """Initialize the chat service and load the workflow."""
        try:
            logger.info("Initializing ChatService...")
            
            # Setup tool path
            tool_path = Path(__file__).parent.parent.parent.parent / "tool"
            if str(tool_path) not in sys.path:
                sys.path.insert(0, str(tool_path))
            
            logger.info(f"Tool path: {tool_path}")
            
            # Use importlib to safely load the tool's modules without polluting
            # the backend's sys.modules namespace collision with 'src'.
            # We load each tool module by its absolute file path and register it
            # under a namespaced key so it never conflicts with backend's 'src.*'.
            self.build_graph, self.GraphState = self._import_tool_workflow(tool_path)
            self.workflow = None
            
            # Pre-import observability helpers inside the tool namespace (Fix #2)
            self.get_langfuse_callback, self.setup_observability = self._import_tool_observability(tool_path)
            
            logger.info("ChatService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatService: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _load_tool_module(tool_path: Path, relative_module_path: str, module_alias: str):
        """Load a module from the tool directory by file path, registered under a namespaced alias."""
        # Convert 'src/workflows/chat.py' -> tool_path/src/workflows/chat.py
        file_path = tool_path / Path(relative_module_path.replace('.', '/') + '.py')
        if not file_path.exists():
            # Try as package __init__.py
            file_path = tool_path / Path(relative_module_path.replace('.', '/')) / '__init__.py'
        
        # Return cached module if already loaded
        if module_alias in sys.modules:
            return sys.modules[module_alias]
        
        spec = importlib.util.spec_from_file_location(module_alias, file_path)
        if spec is None:
            raise ImportError(f"Cannot find tool module at {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_alias] = module
        spec.loader.exec_module(module)
        return module

    @classmethod
    def _import_tool_workflow(cls, tool_path: Path):
        """Import build_graph and GraphState from the tool's workflow module."""
        # The tool's src is on sys.path, so we can use a temporary swap
        # but scoped tightly to only the workflow import with importlib.util
        workflow_file = tool_path / 'src' / 'workflows' / 'chat.py'
        if not workflow_file.exists():
            workflow_file = tool_path / 'src' / 'workflows' / 'chat' / '__init__.py'
        spec = importlib.util.spec_from_file_location('tool.src.workflows.chat', str(workflow_file))
        module = importlib.util.module_from_spec(spec)
        
        # Temporarily swap 'src' so the tool's internal imports resolve correctly
        backend_src = sys.modules.pop('src', None)
        backend_src_submodules = {k: v for k, v in list(sys.modules.items()) if k.startswith('src.')}
        for key in backend_src_submodules:
            sys.modules.pop(key, None)
        
        try:
            sys.modules['tool.src.workflows.chat'] = module
            spec.loader.exec_module(module)
            return module.build_graph, module.GraphState
        finally:
            # Always restore backend's src namespace
            if backend_src is not None:
                sys.modules['src'] = backend_src
            for key, val in backend_src_submodules.items():
                sys.modules[key] = val

    @classmethod
    def _import_tool_observability(cls, tool_path: Path):
        """Import observability helpers from the tool's config module."""
        obs_file = tool_path / 'src' / 'config' / 'observability.py'
        if not obs_file.exists():
            logger.warning("Tool observability module not found, disabling observability")
            return lambda: None, lambda: None
        
        spec = importlib.util.spec_from_file_location('tool.src.config.observability', obs_file)
        module = importlib.util.module_from_spec(spec)
        
        backend_src = sys.modules.pop('src', None)
        backend_src_submodules = {k: v for k, v in list(sys.modules.items()) if k.startswith('src.')}
        for key in backend_src_submodules:
            sys.modules.pop(key, None)
        
        try:
            sys.modules['tool.src.config.observability'] = module
            spec.loader.exec_module(module)
            return getattr(module, 'get_langfuse_callback', lambda: None), getattr(module, 'setup_observability', lambda: None)
        except Exception as e:
            logger.warning(f"Could not import observability module: {e}")
            return lambda: None, lambda: None
        finally:
            if backend_src is not None:
                sys.modules['src'] = backend_src
            for key, val in backend_src_submodules.items():
                sys.modules[key] = val

    def _get_workflow(self):
        """Lazy load the workflow to avoid initialization issues."""
        if self.workflow is None:
            logger.info("Creating workflow instance...")
            self.workflow = self.build_graph()
        return self.workflow
    
    async def process_query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a legal query using the tool's workflow.
        
        Args:
            query: User's legal query
            session_id: Optional session ID for tracking
            
        Returns:
            Dictionary containing the response and metadata
        """
        try:
            logger.info(f"Processing query (session: {session_id}): {query[:100]}...")
            
            # Create initial state
            initial_state = self.GraphState(user_query=query)
            
            # Get workflow and invoke
            workflow = self._get_workflow()
            result = await workflow.ainvoke(initial_state)
            
            # Extract response and metadata
            final_response = result.get("final_response", "")
            case_markdown = result.get("case_retriever_markdown", "")
            case_pdfs = result.get("case_pdf_paths", [])
            
            # Use case_retriever_markdown if no final_response
            response_text = final_response or case_markdown
            
            response_data = {
                "query": query,
                "response": response_text,
                "metadata": {
                    "intent": result.get("intent"),
                    "confidence_score": result.get("confidence_score"),
                    "active_legal_domain": result.get("active_legal_domain"),
                    "next_module": result.get("next_module"),
                    "case_pdf_paths": case_pdfs
                },
                "session_id": session_id
            }
            
            logger.info(f"Query processed successfully (session: {session_id}), response_length: {len(response_text)}, pdfs: {len(case_pdfs)}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            raise
    
    async def handle_websocket(self, websocket: WebSocket, verified_user: dict = None):
        """WebSocket handler with chat history persistence.
        
        Args:
            websocket: The WebSocket connection
            verified_user: The authenticated user dict decoded from JWT (provided by route)
        """
        import uuid
        import json
        from fastapi import WebSocketDisconnect
        from langfuse import get_client
        from ..models.chat import ChatHistory, Message
        from ..models.user import User
        from beanie import PydanticObjectId
        from datetime import datetime

        # Use pre-cached observability helpers (imported at init time — Fix #2)
        self.setup_observability()

        # Extract user identity from verified JWT payload (not from untrusted query params)
        user_id = verified_user.get("id") if verified_user else websocket.query_params.get("user_id")
        session_id = websocket.query_params.get("session_id")
        chat_history = None
        user = None
        
        if user_id:
            try:
                user = await User.get(PydanticObjectId(user_id))
            except Exception:
                logger.warning(f"User not found: {user_id}")
                user = None
        
        # Try to find existing ChatHistory by session_id (its MongoDB _id)
        if user and session_id:
            try:
                chat_history = await ChatHistory.get(PydanticObjectId(session_id), fetch_links=True)
                # Verify user authorization
                if chat_history and str(chat_history.user.id) != str(user.id):
                    logger.warning(f"User {user_id} not authorized for chat {session_id}")
                    chat_history = None
            except Exception as e:
                logger.warning(f"Could not fetch ChatHistory {session_id}: {e}")
                chat_history = None
        
        # If no existing ChatHistory, create a new one
        if not chat_history and user:
            try:
                chat_history = ChatHistory(
                    user=user,
                    title="New Chat",
                    messages=[],
                    status="active"
                )
                await chat_history.insert()
                # Use the newly created ChatHistory's _id as the session_id
                session_id = str(chat_history.id)
                logger.info(f"Created new ChatHistory with ID: {session_id}")
            except Exception as e:
                logger.error(f"Failed to create ChatHistory: {e}", exc_info=True)
                # Continue without persistence if creation fails
                session_id = str(uuid.uuid4())
        
        # If still no user, use a temporary session ID
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.warning(f"Using temporary session ID: {session_id}")

        logger.info(f"WebSocket session established - Chat ID: {session_id}, User: {user_id}")

        langfuse_client = None
        try:
            langfuse_client = get_client()
        except Exception:
            pass

        graph = self.build_graph()
        chat_context = await _extract_last_turn_context(chat_history)
        current_state = {
            "chat_context": chat_context,
        }
        clarification_count = 0
        MAX_CLARIFICATIONS = 5
        iteration = 0

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                msg_type = message.get("type")
                payload = message.get("payload")
                # Optionally support session_id/user_id in message
                msg_session_id = message.get("session_id")
                msg_user_id = message.get("user_id")
                if msg_session_id:
                    session_id = msg_session_id
                if msg_user_id:
                    user_id = msg_user_id
                    try:
                        user = await User.get(PydanticObjectId(user_id))
                    except Exception:
                        user = None
                # Support the simplified format if sent by a different client, but prioritize original protocol
                if not msg_type and message.get("query"):
                    msg_type = "query"
                    payload = message.get("query")

                if msg_type == "query":
                    chat_context = (current_state.get("chat_context") or "").strip()

                    if not chat_context and chat_history:
                        chat_context = await _extract_last_turn_context(chat_history)

                    current_state = {
                        "user_query": payload,
                        "chat_context": chat_context,
                    }
                    clarification_count = 0
                    iteration = 0
                    await websocket.send_json({"type": "status", "payload": "Analyzing query..."})
                    # Persist user message
                    if chat_history:
                        try:
                            user_msg = Message(
                                sender="user", 
                                content=payload, 
                                created_at=datetime.utcnow(),
                                metadata={"chat_context": chat_context}
                            )
                            await user_msg.insert()
                            chat_history.messages.append(user_msg)
                            chat_history.updated_at = datetime.utcnow()
                            await chat_history.save()
                            logger.info(f"Persisted user message to chat {session_id}")
                        except Exception as e:
                            logger.error(f"Failed to persist user message: {e}")

                elif msg_type == "clarification_response":
                    user_answer = payload
                    if current_state.get("pending_clarification"):
                        clarification = current_state["pending_clarification"]
                        history = current_state.get("clarification_history", [])
                        history.append({"question": clarification['question'], "answer": user_answer})
                        stale_flags = {
                            "pending_clarification",
                            "needs_clarification",
                            "ambiguity_remover_scope",
                            "ambiguity_remover_context",
                            "ambiguity_remover_next",
                            "orchestrator_plan",
                        }
                        new_state = {
                            key: value
                            for key, value in current_state.items()
                            if key not in stale_flags
                        }
                        new_state["user_query"] = user_answer
                        new_state["clarification_history"] = history
                        new_state["clarification_counts"] = current_state.get("clarification_counts", {})
                        new_state["chat_context"] = current_state.get("chat_context", "")
                        current_state = new_state
                        await websocket.send_json({"type": "status", "payload": "Processing clarification..."})
                        # Persist clarification response as user message
                        if chat_history:
                            try:
                                chat_ctx = current_state.get("chat_context", "")
                                clar_msg = Message(
                                    sender="user", 
                                    content=user_answer, 
                                    created_at=datetime.utcnow(), 
                                    metadata={"clarification": True, "chat_context": chat_ctx}
                                )
                                await clar_msg.insert()
                                chat_history.messages.append(clar_msg)
                                chat_history.updated_at = datetime.utcnow()
                                await chat_history.save()
                                logger.info(f"Persisted clarification response to chat {session_id}")
                            except Exception as e:
                                logger.error(f"Failed to persist clarification response: {e}")
                    else:
                        await websocket.send_json({"type": "error", "payload": "No pending clarification found."})
                        continue
                else:
                    await websocket.send_json({"type": "error", "payload": f"Unknown message type: {msg_type}"})
                    continue

                # Run the Graph Loop (until result or next clarification)
                while True:
                    iteration += 1
                    
                    # Setup callback using pre-cached helper (Fix #2)
                    callback_handler = self.get_langfuse_callback()
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
                        
                        # Fallback if streaming didn't capture state (Fix #3: always async)
                        if not final_state:
                            final_state = await graph.ainvoke(current_state, config=config)
                            
                    except Exception as e:
                        logger.error(f"Graph execution failed: {e}")
                        # Async fallback only — never block the event loop with sync invoke
                        final_state = await graph.ainvoke(current_state, config=config)
                    
                    # Check for clarification
                    if final_state.get("pending_clarification"):
                        clarification_count += 1
                        if clarification_count > MAX_CLARIFICATIONS:
                            await websocket.send_json({"type": "status", "payload": "Max clarifications reached. Proceeding..."})
                            current_state = {**final_state}
                            if "pending_clarification" in current_state:
                                del current_state["pending_clarification"]
                            if "orchestrator_plan" in current_state:
                                del current_state["orchestrator_plan"]
                            continue
                        clarification = final_state["pending_clarification"]
                        current_state = final_state
                        response_payload = {
                            "question": clarification['question'],
                            "reason": clarification.get('reason'),
                            "options": clarification.get('options')
                        }
                        await websocket.send_json({"type": "clarification_request", "payload": response_payload})
                        # Persist clarification as assistant message
                        if chat_history:
                            try:
                                from ..models.chat import Message
                                chat_ctx = current_state.get("chat_context", "")
                                clar_msg = Message(
                                    sender="assistant", 
                                    content=clarification['question'], 
                                    created_at=datetime.utcnow(), 
                                    metadata={"clarification": True, "chat_context": chat_ctx}
                                )
                                await clar_msg.insert()
                                chat_history.messages.append(clar_msg)
                                chat_history.updated_at = datetime.utcnow()
                                await chat_history.save()
                                logger.info(f"Persisted clarification request to chat {session_id}")
                            except Exception as e:
                                logger.error(f"Failed to persist clarification request: {e}")
                        if langfuse_client:
                            try:
                                langfuse_client.flush()
                            except: pass
                        break
                    # If no clarification, we have a result!
                    router_output = final_state.get("router_output")
                    final_response = final_state.get("final_response")
                    case_retriever_markdown = final_state.get("case_retriever_markdown")
                    case_pdf_paths = final_state.get("case_pdf_paths", [])
                    generated_document_content = final_state.get("generated_document_content")
                    procedural_state = (
                        final_state.get("procedural_guidance_civil_state") or 
                        final_state.get("procedural_guidance_criminal_state") or
                        final_state.get("procedural_guidance_state")
                    )
                    activity_state = final_state.get("activity_law_state")
                    result_payload = {}
                    if generated_document_content:
                        result_payload["document_content"] = generated_document_content
                    
                    # Use case_retriever_markdown as text if available, otherwise use final_response
                    if case_retriever_markdown and isinstance(case_retriever_markdown, str) and case_retriever_markdown.strip():
                        result_payload["text"] = case_retriever_markdown
                        logger.info(f"Using case_retriever_markdown as final response text")
                    elif final_response:
                        result_payload["text"] = final_response
                    
                    # Include case PDF paths in final result
                    if case_pdf_paths and isinstance(case_pdf_paths, list) and len(case_pdf_paths) > 0:
                        result_payload["case_pdf_paths"] = case_pdf_paths
                        logger.info(f"Including {len(case_pdf_paths)} case PDF paths in final result")
                    elif procedural_state:
                        result_payload["workflow"] = "procedural"
                        if isinstance(procedural_state, dict):
                            proc_dict = procedural_state
                        else:
                            proc_dict = procedural_state.model_dump() if hasattr(procedural_state, 'model_dump') else procedural_state.dict()
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

                    if final_response:
                        # Build new chat_context from current turn
                        new_chat_context = f"Previous exchange:\nUser: {(current_state.get('user_query') or '').strip()}\nAssistant: {final_response}"
                        final_state["chat_context"] = new_chat_context

                    await websocket.send_json({"type": "final_result", "payload": result_payload})
                    # Persist assistant/system message
                    if chat_history:
                        try:
                            from ..models.chat import Message
                            content = result_payload.get("text") or json.dumps(result_payload)
                            
                            # Build document field if there's generated document content
                            document_field = None
                            if generated_document_content:
                                document_field = {"content": generated_document_content}
                            
                            # Build metadata including case_pdf_paths
                            chat_ctx = final_state.get("chat_context", "")
                            metadata = {
                                "final_result": True, 
                                "chat_context": chat_ctx
                            }
                            if case_pdf_paths and isinstance(case_pdf_paths, list) and len(case_pdf_paths) > 0:
                                metadata["case_pdf_paths"] = case_pdf_paths
                            
                            assist_msg = Message(
                                sender="assistant", 
                                content=content, 
                                document=document_field,
                                created_at=datetime.utcnow(), 
                                metadata=metadata
                            )
                            await assist_msg.insert()
                            chat_history.messages.append(assist_msg)
                            chat_history.updated_at = datetime.utcnow()
                            await chat_history.save()
                            logger.info(f"Persisted final result to chat {session_id} with {len(case_pdf_paths) if case_pdf_paths else 0} PDFs")
                        except Exception as e:
                            logger.error(f"Failed to persist final result: {e}")
                    if langfuse_client:
                        try:
                            langfuse_client.flush()
                        except: pass
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket session disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
            try:
               await websocket.send_json({"type": "error", "payload": str(e)})
            except:
               pass
