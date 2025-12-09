from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class FactFactor(BaseModel):
    """A legally relevant factual element."""
    factor_id: str = Field(..., description="Unique ID for the factor (e.g., F1, F2)")
    type: str = Field(..., description="Type of factor: person, date, location, action, etc.")
    value: str = Field(..., description="The value or description of the factor")

class Event(BaseModel):
    """A specific event in the chronological sequence."""
    event_id: str = Field(..., description="Unique ID for the event (e.g., E1, E2)")
    time: Optional[str] = Field(None, description="Approximate time/date if inferable")
    actors: List[str] = Field(default_factory=list, description="List of actors involved")
    location: Optional[str] = Field(None, description="Location of the event")
    action: str = Field(..., description="The action that took place")
    description: str = Field(..., description="Natural language description of the event")

class FactStructuringOutput(BaseModel):
    """Output of the Fact Structuring Agent."""
    factors: List[FactFactor]
    events: List[Event]

class StatuteMatch(BaseModel):
    """A candidate statute provision."""
    provision: str = Field(..., description="The statutory provision (e.g., 'IPC Section 378')")
    match_score: float = Field(..., description="Match score between 0.0 and 1.0")
    reasoning: str = Field(..., description="Why this statute is a candidate")

class StatuteMatchingOutput(BaseModel):
    """Output of the Statute Matching Agent."""
    candidate_statutes: List[StatuteMatch]

class RuleMatch(BaseModel):
    """Applicability decision for a statute."""
    provision: str = Field(..., description="The statutory provision")
    applicability: Literal["applicable", "uncertain", "not_applicable"] = Field(..., description="Applicability status")
    notes: str = Field(..., description="Explanation of applicability rules/exceptions")

class RuleMatchingOutput(BaseModel):
    """Output of the Rule Matching Agent."""
    rule_assessments: List[RuleMatch]

class RiskAssessment(BaseModel):
    """Risk assessment for an applicable provision."""
    provision: str = Field(..., description="The statute provision")
    likelihood_of_applicability: float = Field(..., description="Probability of applicability 0.0-1.0")
    potential_penalty: str = Field(..., description="Summary of potential penalties")
    recommended_action: str = Field(..., description="Recommended next steps")

class RiskAssessmentOutput(BaseModel):
    """Output of the Risk Assessment Agent."""
    risk_matrix: List[RiskAssessment]

class EvidenceLink(BaseModel):
    """Link between a statute element and supporting facts/events."""
    element: str = Field(..., description="The statutory element (e.g., 'Dishonest Intention')")
    supporting_fact_ids: List[str] = Field(default_factory=list, description="IDs of supporting factors")
    supporting_event_ids: List[str] = Field(default_factory=list, description="IDs of supporting events")
    evidence_confidence: float = Field(..., description="Confidence that facts support this element (0-1)")

class ProvisionEvidence(BaseModel):
    """Evidence mapping for a specific provision."""
    provision: str = Field(..., description="The statute provision")
    element_mappings: List[EvidenceLink]
    explanation: str = Field(..., description="Summary explanation of why this provision applies")

class EvidenceLinkingOutput(BaseModel):
    """Output of the Evidence Linking Agent."""
    evidence_links: List[ProvisionEvidence]

class ActivityLawState(BaseModel):
    """Accumulated state for the Activity to Law Workflow."""
    fact_structuring: Optional[FactStructuringOutput] = None
    statute_matching: Optional[StatuteMatchingOutput] = None
    rule_matching: Optional[RuleMatchingOutput] = None
    risk_assessment: Optional[RiskAssessmentOutput] = None
    evidence_linking: Optional[EvidenceLinkingOutput] = None
