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
from typing import Optional

from src.models import GraphState
from src.agents.ambiguity_remover import AmbiguityRemover, ClarificationRequest
from langchain_core.runnables import RunnableConfig

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
    
    # Determine which agent is requesting (based on scope or tracking)
    agent_key = state.get("current_agent", scope)
    current_count = clarification_counts.get(agent_key, 0)
    
    logger.info(
        f"AmbiguityRemover: Processing clarification request "
        f"(scope={scope}, agent={agent_key}, count={current_count})"
    )
    
    # Extract callbacks from config for LangFuse integration
    callbacks = config.get("callbacks", []) if config else []
    
    # Invoke AmbiguityRemover with callbacks
    try:
        result = await _ambiguity_remover.assess_and_clarify(
            user_query=state.get("user_query", ""),
            agent_context=agent_context,
            scope=scope,
            expertise_level=state.get("user_expertise_level", "general_public"),
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
            "ambiguity_remover_scope": None,  # Clear the flag
            "ambiguity_remover_context": None,
        }
    
    return {}
