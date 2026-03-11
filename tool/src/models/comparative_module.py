from typing import List

from pydantic import BaseModel, Field


class ComparisonEntry(BaseModel):
    """Metadata for a precomputed state-law comparison table."""

    id: str = Field(..., description="Unique ID for the comparison entry")
    topic: str = Field(..., description="Comparison topic")
    states: List[str] = Field(..., description="States covered by this table")
    keywords: List[str] = Field(default_factory=list, description="Keywords for query matching")
    aliases: List[str] = Field(default_factory=list, description="Alias terms for query matching")
    file_path: str = Field(..., description="Relative markdown source path")
    has_table: bool = Field(False, description="Whether source contains a markdown table")
    table_headers: List[str] = Field(default_factory=lambda: ["Aspect", "State 1", "State 2"])
    table_row_count: int = Field(0, description="Approximate number of table rows")
    short_summary: str = Field("", description="Short description of this comparison")


class ComparisonMatch(BaseModel):
    """Top match result for a user query against comparison metadata."""

    entry: ComparisonEntry
    score: float = Field(..., description="Aggregate matching score")
    matched_terms: List[str] = Field(default_factory=list, description="Matched terms from query")


class ComparativeStateFinding(BaseModel):
    """A single state-specific finding for a legal aspect."""

    aspect: str = Field(..., description="Legal aspect label")
    value: str = Field(..., description="State-specific legal position for the aspect")


class ComparativeAgent1Output(BaseModel):
    """Agent 1 output: states extraction + clarification decision."""

    needs_clarification: bool = Field(..., description="Whether clarification is needed before proceeding")
    state_1: str = Field("", description="Primary state for comparison")
    state_2: str = Field("", description="Secondary state for comparison")
    topic_hint: str = Field("", description="Inferred comparison topic from query")
    reasoning: str = Field("", description="Short reasoning for extraction result")
    clarification_question: str = Field("", description="Clarification prompt if states are missing")


class ComparativeStateFindingsOutput(BaseModel):
    """Agent 2/3 output: findings for one state."""

    findings: List[ComparativeStateFinding] = Field(default_factory=list)
    summary: str = Field("", description="Summary of extracted findings")


class ComparativeAgent4Output(BaseModel):
    """Agent 4 output: final response sections."""

    intro: str = Field(..., description="Introductory paragraph")
    table_markdown: str = Field(..., description="Comparison table in markdown")
    conclusion: str = Field(..., description="Concluding paragraph")
