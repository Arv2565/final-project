"""
AmbiguityRemover Agent

A pluggable agent that handles clarification question generation for any agent
that needs ambiguous information clarified. Replaces decentralized clarification
logic with a centralized, domain-aware approach that:

1. Uses specialized system prompts per domain (factual, activity, procedural, etc.)
2. Simplifies legal jargon for non-legal users
3. Evaluates necessity (only asks when truly needed)
4. Tracks clarification effectiveness (only stores useful Q&A pairs)
5. Provides a plugin interface for adding new domains

Usage:
    ambiguity_remover = AmbiguityRemover(llm=chat_model)
    result = await ambiguity_remover.assess_and_clarify(
        user_query="...",
        agent_context={"extracted_facts": {...}, "missing": [...]},
        scope="factual",
        expertise_level="general_public"
    )
    
    if result["needs_clarification"]:
        # Process clarification_request
        pass
"""

import uuid
import logging
from typing import Dict, Optional, List, Union, Callable, Any
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class ClarificationRequest(BaseModel):
    """Structured clarification question for users."""
    
    question: str = Field(..., description="The clarification question in simple language")
    reason: str = Field(..., description="Why this clarification is needed (user-friendly explanation)")
    options: Optional[List[str]] = Field(default=None, description="Optional predefined choices")
    importance: str = Field(default="medium", description="Priority: 'low', 'medium', 'high'")
    
    # Tracking fields
    clarification_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for this clarification")
    scope: str = Field(..., description="Domain scope: 'factual', 'activity', 'procedural', etc.")
    is_used: bool = Field(default=False, description="Whether this clarification resolved ambiguity")
    resolution_feedback: Optional[str] = Field(default=None, description="Why clarification was/wasn't useful")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this clarification was created")


class ClarificationResult(BaseModel):
    """Result from AmbiguityRemover assessment."""
    
    needs_clarification: bool
    clarification_request: Optional[ClarificationRequest] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="0-1 confidence in current understanding")
    reasoning: str = Field(..., description="Why clarification is/isn't needed")


class AmbiguityRemover:
    """
    Pluggable agent for intelligently requesting clarifications.
    
    Handles:
    - Domain-specific clarification question generation
    - Jargon simplification for general users
    - Necessity evaluation (only asks when needed)
    - Effectiveness tracking (marks which clarifications actually helped)
    - Plugin interface for custom domains
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        default_domains: Optional[Dict[str, Union[str, Callable]]] = None,
        max_clarifications_per_agent: int = 3,
        max_total_clarifications: int = 5,
    ):
        """
        Initialize AmbiguityRemover.
        
        Args:
            llm: Language model for clarification generation
            default_domains: Dict of {domain_name: system_prompt_or_callable}
                           Will be populated with factual/activity/procedural if None
            max_clarifications_per_agent: Max clarifications per agent before forcing best-guess
            max_total_clarifications: Max total clarifications per query across all agents
        """
        self.llm = llm
        self.domain_prompts: Dict[str, Union[str, Callable]] = default_domains or {}
        self.max_clarifications_per_agent = max_clarifications_per_agent
        self.max_total_clarifications = max_total_clarifications
        
        # Load default domain prompts if not provided
        if not default_domains:
            self._load_default_prompts()
    
    def _load_default_prompts(self) -> None:
        """Load default domain prompts. Override to customize."""
        try:
            from src.prompts.ambiguity_remover import (
                factual_prompt,
                activity_prompt,
                procedural_prompt,
            )
            
            self.domain_prompts = {
                "factual": factual_prompt.get_system_prompt,
                "activity": activity_prompt.get_system_prompt,
                "procedural": procedural_prompt.get_system_prompt,
            }
            logger.info(f"Loaded default domain prompts: {list(self.domain_prompts.keys())}")
        except ImportError as e:
            logger.warning(f"Could not load default domain prompts: {e}")
            self.domain_prompts = {}
    
    def register_domain_prompt(
        self,
        domain: str,
        system_prompt: Union[str, Callable[[str, Dict], str]],
    ) -> None:
        """
        Register a new domain with its system prompt.
        
        Args:
            domain: Domain name (e.g., 'contractual', 'ip_law', 'custom')
            system_prompt: Either a static prompt string or a callable that generates
                          the prompt based on (expertise_level: str, context: Dict) -> str
        
        Example:
            ambiguity_remover.register_domain_prompt(
                "contract_review",
                system_prompt=my_contract_prompt_fn
            )
        """
        self.domain_prompts[domain] = system_prompt
        logger.info(f"Registered domain '{domain}' for AmbiguityRemover")
    
    def get_registered_domains(self) -> List[str]:
        """Return list of available domain scopes."""
        return list(self.domain_prompts.keys())
    
    def _get_system_prompt(
        self,
        scope: str,
        expertise_level: str = "general_public",
        context: Optional[Dict] = None,
    ) -> str:
        """
        Get the system prompt for a given scope.
        
        Args:
            scope: Domain scope (e.g., 'factual', 'activity')
            expertise_level: User expertise ('general_public', 'educated_layperson', 'legal_professional')
            context: Additional context dict
        
        Returns:
            System prompt string
        """
        if scope not in self.domain_prompts:
            raise ValueError(
                f"Unknown scope '{scope}'. Registered domains: {self.get_registered_domains()}"
            )
        
        prompt_or_callable = self.domain_prompts[scope]
        
        # If it's a callable, invoke it with parameters
        if callable(prompt_or_callable):
            return prompt_or_callable(
                expertise_level=expertise_level,
                context=context or {}
            )
        
        # Otherwise, return the static string
        return prompt_or_callable
    
    async def assess_and_clarify(
        self,
        user_query: str,
        agent_context: Dict,
        scope: str,
        expertise_level: str = "general_public",
        clarification_count: int = 0,
        config: Optional[RunnableConfig] = None,
    ) -> ClarificationResult:
        """
        Assess if clarification is needed and generate clarification request.
        
        Args:
            user_query: Original user query
            agent_context: Context from calling agent (e.g., {'extracted_facts': {...}, 'missing': [...]})
            scope: Domain scope ('factual', 'activity', 'procedural', etc.)
            expertise_level: User expertise level for prompt tailoring
            clarification_count: Current clarification count for this agent
            config: Runnable config
        
        Returns:
            ClarificationResult with needs_clarification, clarification_request, confidence, reasoning
        
        Raises:
            ValueError: If scope not registered
        """
        # Check if at max clarifications
        if clarification_count >= self.max_clarifications_per_agent:
            logger.info(
                f"Agent at max clarifications ({clarification_count}). "
                f"Will not request further clarification."
            )
            return ClarificationResult(
                needs_clarification=False,
                confidence=0.3,
                reasoning=(
                    f"Maximum clarification attempts ({self.max_clarifications_per_agent}) "
                    f"reached for this agent. Making best-guess decision."
                ),
            )
        
        # Get domain-specific system prompt
        try:
            system_prompt = self._get_system_prompt(
                scope=scope,
                expertise_level=expertise_level,
                context=agent_context,
            )
        except ValueError as e:
            logger.error(str(e))
            raise
        
        # Prepare message for LLM
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=self._prepare_user_message(user_query, agent_context)),
        ]
        
        # Invoke LLM
        try:
            response = await self.llm.ainvoke(messages, config=config)
            result = self._parse_llm_response(response.content, scope)
            return result
        except Exception as e:
            logger.error(f"Error in AmbiguityRemover assessment: {e}")
            # On error, don't request clarification—let agent proceed
            return ClarificationResult(
                needs_clarification=False,
                confidence=0.0,
                reasoning=f"Error in clarification assessment: {e}",
            )
    
    def _prepare_user_message(self, user_query: str, agent_context: Dict) -> str:
        """
        Format the user message for the LLM with context.
        
        Args:
            user_query: Original user query
            agent_context: Agent's extracted context
        
        Returns:
            Formatted message
        """
        message = f"User query: {user_query}\n\nAgent context:\n"
        
        for key, value in agent_context.items():
            if isinstance(value, list):
                message += f"- {key}: {', '.join(str(v) for v in value)}\n"
            elif isinstance(value, dict):
                message += f"- {key}: {value}\n"
            else:
                message += f"- {key}: {value}\n"
        
        message += "\nDetermine: (1) Is clarification necessary? (2) If yes, what's the simplest question to ask?"
        return message
    
    def _parse_llm_response(self, content: str, scope: str) -> ClarificationResult:
        """
        Parse LLM response into ClarificationResult.
        
        Expects response format (but flexible):
        NEEDS_CLARIFICATION: yes|no
        CONFIDENCE: 0.0-1.0
        QUESTION: [simplified question text]
        REASON: [why it's needed, in simple terms]
        OPTIONS: [comma-separated options, or 'None']
        IMPORTANCE: low|medium|high
        REASONING: [explanation of decision]
        
        Args:
            content: LLM response text
            scope: Domain scope for clarification
        
        Returns:
            Parsed ClarificationResult
        """
        lines = content.strip().split("\n")
        parsed = {}
        
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                parsed[key.strip().lower()] = value.strip()
        
        # Determine if clarification needed
        needs_clarification = parsed.get("needs_clarification", "").lower() in ["yes", "true"]
        
        if not needs_clarification:
            return ClarificationResult(
                needs_clarification=False,
                confidence=float(parsed.get("confidence", "0.7")),
                reasoning=parsed.get("reasoning", "Sufficient information available"),
            )
        
        # Parse clarification request
        question = parsed.get("question", "Could you provide more information?")
        reason = parsed.get("reason", "To better understand your situation")
        importance = parsed.get("importance", "medium")
        options_str = parsed.get("options", "None")
        
        options = None
        if options_str and options_str.lower() != "none":
            options = [opt.strip() for opt in options_str.split(",")]
        
        clarification_request = ClarificationRequest(
            question=question,
            reason=reason,
            options=options,
            importance=importance,
            scope=scope,
        )
        
        return ClarificationResult(
            needs_clarification=True,
            clarification_request=clarification_request,
            confidence=float(parsed.get("confidence", "0.5")),
            reasoning=parsed.get("reasoning", "Clarification needed to proceed"),
        )
    
    def mark_clarification_used(
        self,
        clarification_id: str,
        clarification_history: List[Dict],
        resolution_feedback: str = "",
    ) -> List[Dict]:
        """
        Mark a clarification as used/helpful in the history.
        
        Args:
            clarification_id: ID of clarification to mark
            clarification_history: Current history list
            resolution_feedback: Explanation of how it resolved ambiguity
        
        Returns:
            Updated clarification history
        """
        for item in clarification_history:
            if item.get("clarification_id") == clarification_id:
                item["is_used"] = True
                item["resolution_feedback"] = resolution_feedback
                logger.info(f"Marked clarification {clarification_id} as used: {resolution_feedback}")
                break
        
        return clarification_history
    
    def get_useful_history(
        self,
        clarification_history: List[Dict],
    ) -> List[Dict]:
        """
        Filter history to only useful clarifications (is_used=True).
        
        Args:
            clarification_history: Full history
        
        Returns:
            Filtered history with only used clarifications
        """
        useful = [
            item for item in clarification_history
            if item.get("is_used", False)
        ]
        logger.info(f"Filtered history: {len(clarification_history)} total → {len(useful)} useful")
        return useful
    
    def cleanup_unused_clarifications(
        self,
        clarification_history: List[Dict],
    ) -> Dict[str, Any]:
        """
        Remove unused clarifications and return cleanup stats.
        
        Args:
            clarification_history: History to clean
        
        Returns:
            Dict with stats about cleanup
        """
        original_count = len(clarification_history)
        useful = self.get_useful_history(clarification_history)
        unused_count = original_count - len(useful)
        
        stats = {
            "original_count": original_count,
            "useful_count": len(useful),
            "unused_removed": unused_count,
        }
        
        if unused_count > 0:
            logger.info(
                f"Cleanup: Removed {unused_count} unused clarifications "
                f"({len(useful)} kept, {unused_count} discarded)"
            )
        
        return stats
