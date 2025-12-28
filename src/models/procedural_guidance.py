from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TimelineConstraint(BaseModel):
    """A deadline, limitation period, or filing window."""
    constraint_id: str = Field(..., description="Unique ID for the constraint (e.g., TC1, TC2)")
    constraint_type: Literal["filing_deadline", "limitation_period", "hearing_date", "response_window", "appeal_window"] = Field(
        ..., description="Type of time constraint"
    )
    description: str = Field(..., description="Natural language description of the constraint")
    statutory_reference: str = Field(..., description="BNSS/Evidence Act section reference")
    time_limit: str = Field(..., description="Time limit or deadline (e.g., '3 months from offense')")
    consequences: str = Field(..., description="Consequences of missing this deadline")


class TimelineConstraintOutput(BaseModel):
    """Output of the Timeline/Constraint Identifier Agent."""
    constraints: List[TimelineConstraint] = Field(
        default_factory=list,
        description="List of identified timeline constraints"
    )


class ChecklistItem(BaseModel):
    """An item to prepare for the procedural step."""
    item_id: str = Field(..., description="Unique ID for the item (e.g., CL1, CL2)")
    description: str = Field(..., description="What needs to be prepared")
    priority: Literal["high", "medium", "low"] = Field(..., description="Priority level")
    reason: str = Field(..., description="Why this item is needed")
    statutory_basis: str = Field(..., description="Legal basis (BNSS/Evidence Act section)")
    related_constraint_ids: List[str] = Field(
        default_factory=list,
        description="IDs of related timeline constraints"
    )


class ChecklistOutput(BaseModel):
    """Output of the Checklist Generator Agent."""
    items: List[ChecklistItem] = Field(
        default_factory=list,
        description="Prioritized list of items to prepare"
    )


class ResponsibleActor(BaseModel):
    """A party or officer responsible for a procedural step."""
    step: str = Field(..., description="The procedural step or action")
    responsible_party: str = Field(..., description="Party responsible (e.g., Complainant, Accused)")
    responsible_officer: Optional[str] = Field(None, description="Officer responsible (e.g., SHO, Magistrate)")
    statutory_reference: str = Field(..., description="BNSS section defining this responsibility")
    contact_info: str = Field(..., description="How to contact or where to go")


class ActorMappingOutput(BaseModel):
    """Output of the Responsible Actor Mapper Agent."""
    actor_mappings: List[ResponsibleActor] = Field(
        default_factory=list,
        description="Mapping of steps to responsible actors"
    )


class ProceduralStep(BaseModel):
    """A single ordered procedural step."""
    step_number: int = Field(..., description="Sequential step number")
    action: str = Field(..., description="What action to take")
    responsible_actors: List[str] = Field(
        default_factory=list,
        description="Who is responsible (parties and officers)"
    )
    estimated_time: str = Field(..., description="Time estimate for this step")
    estimated_cost: str = Field(..., description="Cost estimate for this step")
    required_documents: List[str] = Field(
        default_factory=list,
        description="Documents required for this step"
    )
    forms: List[str] = Field(
        default_factory=list,
        description="Forms to fill (with URLs if available)"
    )
    contact_points: List[str] = Field(
        default_factory=list,
        description="Where to go or who to contact"
    )
    statutory_reference: str = Field(..., description="BNSS/Evidence Act reference")


class EstimatedEffortOutput(BaseModel):
    """Output of the Estimated Effort Agent."""
    ordered_steps: List[ProceduralStep] = Field(
        default_factory=list,
        description="Final ordered procedural steps"
    )
    total_estimated_time: str = Field(..., description="Total time estimate for entire process")
    total_estimated_cost: str = Field(..., description="Total cost estimate")


class ProceduralGuidanceState(BaseModel):
    """Accumulated state for the Procedural Guidance Workflow."""
    timeline_constraints: Optional[TimelineConstraintOutput] = None
    checklist: Optional[ChecklistOutput] = None
    actor_mapping: Optional[ActorMappingOutput] = None
    estimated_effort: Optional[EstimatedEffortOutput] = None
