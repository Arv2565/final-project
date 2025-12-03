from typing import TypedDict, NotRequired


class GraphState(TypedDict, total=False):
    """Shared state passed through the LangGraph workflow.

    Fields:
        question:     Original user question.
        instructions: Optional extra instructions for the writer.
        research_notes: Structured notes produced by ResearchAgent.
        answer:       Final, polished answer from WriterAgent.
    """

    question: str
    instructions: NotRequired[str]
    research_notes: NotRequired[str]
    answer: NotRequired[str]
