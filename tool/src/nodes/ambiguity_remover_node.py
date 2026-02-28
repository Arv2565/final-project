"""
AmbiguityRemover workflow node.

Integrates the AmbiguityRemover agent into the workflow as a dedicated node
that normalizes clarification requests across all domains.

This node:
1. Checks if an agent flagged uncertainty
2. Invokes AmbiguityRemover with appropriate domain scope
3. Returns standardized ClarificationRequest
4. Tracks clarification history and effectiveness
5. Integrates with LangFuse for observability
"""

import logging
import asyncio
from typing import Optional

from src.models import GraphState
from src.agents.ambiguity_remover import AmbiguityRemover, ClarificationRequest
from langchain_core.runnables import RunnableConfig, RunnableLambda

logger = logging.getLogger(__name__)

# Global AmbiguityRemover instance (will be initialized in workflow builder)
_ambiguity_remover: Optional[AmbiguityRemover] = None


def set_ambiguity_remover(remover: AmbiguityRemover) -> None:
    """Set the global AmbiguityRemover instance."""
    global _ambiguity_remover
    _ambiguity_remover = remover
    logger.info("AmbiguityRemover instance set in workflow")


def get_ambiguity_remover() -> Optional[AmbiguityRemover]:
    """Get the global AmbiguityRemover instance."""
    return _ambiguity_remover


async def ambiguity_remover_node(state: GraphState, config: Optional[RunnableConfig] = None) -> dict:
    """
    AmbiguityRemover workflow node.
    
    Checks if an agent flagged a need for clarification via ambiguity_remover_scope.
    If so, invokes the AmbiguityRemover to generate a simplified, user-friendly
    clarification question.
    
    This node is fully instrumented with LangFuse for observability tracking.
    
    Args:
        state: Current graph state
        config: Runnable config containing callbacks for observability
    
    Returns:
        Updated state with pending_clarification and clarification_counts
    """
    
    if _ambiguity_remover is None:
        logger.error("AmbiguityRemover not initialized. Cannot process clarification.")
        return {}
    
    # Check if clarification is needed
    scope = state.get("ambiguity_remover_scope")
    if not scope or not state.get("needs_clarification"):
        return {}
    
    # Get agent context and clarification count
    agent_context = state.get("ambiguity_remover_context", {})
    clarification_counts = state.get("clarification_counts", {})
    
    # Extract language from router_output (use original language for clarifications, not translated)
    router_output = state.get("router_output")
    language = "en"  # Default to English
    if router_output and router_output.metadata:
        # Use original_language if available (what user actually speaks)
        # Fall back to language field if original_language not set
        language = router_output.metadata.original_language or router_output.metadata.language or "en"
    
    # Determine which agent is requesting (based on scope or tracking)
    agent_key = state.get("current_agent", scope)
    current_count = clarification_counts.get(agent_key, 0)
    
    logger.info(
        f"AmbiguityRemover: Processing clarification request "
        f"(scope={scope}, agent={agent_key}, count={current_count}, language={language})"
    )

    # If upstream agent already produced a concrete clarification question,
    # localize/rephrase it through LLM so language is consistent and traceable.
    predefined_question = agent_context.get("agent_requested_question") if isinstance(agent_context, dict) else None
    if predefined_question:
        predefined_reason = agent_context.get("agent_requested_reason") or "To better understand your situation"
        predefined_options = agent_context.get("agent_requested_options")

        localized_question = predefined_question
        localized_reason = predefined_reason
        localized_options = predefined_options

        callbacks = config.get("callbacks", []) if config else []
        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            options_text = ", ".join(predefined_options) if predefined_options else "None"
            messages = [
                SystemMessage(
                    content=(
                        "You are a legal assistant localization helper. "
                        f"Rewrite the provided clarification for a layperson in language code '{language}'. "
                        "Keep legal references intact, preserve meaning, and keep it simple. "
                        "Return exactly this format:\n"
                        "QUESTION: ...\nREASON: ...\nOPTIONS: opt1, opt2 OR None"
                    )
                ),
                HumanMessage(
                    content=(
                        f"QUESTION: {predefined_question}\n"
                        f"REASON: {predefined_reason}\n"
                        f"OPTIONS: {options_text}"
                    )
                ),
            ]

            response = await _ambiguity_remover.llm.ainvoke(
                messages,
                config={"callbacks": callbacks} if callbacks else None,
            )
            parsed = {}
            for line in response.content.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    parsed[key.strip().lower()] = value.strip()

            localized_question = parsed.get("question", localized_question)
            localized_reason = parsed.get("reason", localized_reason)
            options_str = parsed.get("options")
            if options_str:
                localized_options = None if options_str.lower() == "none" else [opt.strip() for opt in options_str.split(",") if opt.strip()]
        except Exception as e:
            logger.warning(f"AmbiguityRemover localization failed, using original clarification: {e}")

        clarification = ClarificationRequest(
            question=localized_question,
            reason=localized_reason,
            options=localized_options,
            importance="medium",
            scope=scope,
        )

        clarification_counts[agent_key] = current_count + 1
        logger.info("AmbiguityRemover: Localized predefined clarification from upstream agent context")
        return {
            "pending_clarification": clarification.dict(),
            "clarification_counts": clarification_counts,
            "needs_clarification": False,
            "ambiguity_remover_scope": None,
            "ambiguity_remover_context": None,
            "ambiguity_remover_next": None,
        }
    
    # Extract callbacks from config for LangFuse integration
    callbacks = config.get("callbacks", []) if config else []
    
    # Invoke AmbiguityRemover with callbacks
    try:
        result = await _ambiguity_remover.assess_and_clarify(
            user_query=state.get("user_query", ""),
            agent_context=agent_context,
            scope=scope,
            expertise_level=state.get("user_expertise_level", "general_public"),
            language=language,
            clarification_count=current_count,
            config={"callbacks": callbacks} if callbacks else None,
        )
    except ValueError as e:
        logger.error(f"AmbiguityRemover error: {e}. Proceeding without clarification.")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error in AmbiguityRemover: {e}")
        return {}
    
    # If no clarification needed, clear the flags and continue
    if not result.needs_clarification:
        logger.info(f"AmbiguityRemover decided clarification not needed (confidence={result.confidence})")
        return {
            "ambiguity_remover_scope": None,
            "ambiguity_remover_context": None,
            "needs_clarification": False,
            "ambiguity_remover_next": None,
        }
    
    # If clarification needed, update counts and return clarification request
    if result.clarification_request:
        clarification_counts[agent_key] = current_count + 1
        
        # Initialize clarification history if needed
        clarification_history = state.get("clarification_history", [])
        
        logger.info(
            f"AmbiguityRemover generated clarification: {result.clarification_request.question} "
            f"(importance={result.clarification_request.importance})"
        )
        
        return {
            "pending_clarification": result.clarification_request.dict(),
            "clarification_counts": clarification_counts,
            "needs_clarification": False,
            "ambiguity_remover_scope": None,  # Clear the flag
            "ambiguity_remover_context": None,
            "ambiguity_remover_next": None,
        }
    
    return {}


def ambiguity_remover_node_sync(state: GraphState, config: Optional[RunnableConfig] = None) -> dict:
    """Synchronous wrapper for ambiguity_remover_node to support graph.invoke()."""
    return asyncio.run(ambiguity_remover_node(state, config=config))


ambiguity_remover_runnable = RunnableLambda(
    func=ambiguity_remover_node_sync,
    afunc=ambiguity_remover_node,
    name="ambiguity_remover",
)
