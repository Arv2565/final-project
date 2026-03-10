from unittest.mock import MagicMock, patch

from src.agents.document_generation.document_generation_agent import DocumentGenerationAgent


def _build_agent() -> DocumentGenerationAgent:
    with patch("src.agents.document_generation.document_generation_agent.get_agent_llm"):
        return DocumentGenerationAgent()


def test_unwraps_soft_line_break_after_ms_prefix():
    agent = _build_agent()
    sample = "1- That my client is under the name and style of M/s\nVertex Innovations Pvt. Ltd."

    normalized = agent._normalize_generated_document(sample)

    assert "M/s Vertex Innovations Pvt. Ltd." in normalized
    assert "M/s\nVertex" not in normalized


def test_preserves_numbered_and_lettered_clause_boundaries():
    agent = _build_agent()
    sample = "1- First clause line\nthat continues here\n2- Second clause\na. Sub clause start\ncontinuation line"

    normalized = agent._normalize_generated_document(sample)

    assert "1- First clause line that continues here" in normalized
    assert "\n2- Second clause\n" in normalized
    assert "\na. Sub clause start continuation line" in normalized


def test_preserves_address_block_line_breaks_between_to_and_dear_sir():
    agent = _build_agent()
    sample = "To,\nOrion Digital Solutions Pvt. Ltd.,\nPlot No. 21, Tech Park Avenue,\nBengaluru 560103\nDear Sir,\nPursuant to instructions from my client"

    normalized = agent._normalize_generated_document(sample)

    assert "To,\nOrion Digital Solutions Pvt. Ltd.,\nPlot No. 21, Tech Park Avenue,\nBengaluru 560103\nDear Sir," in normalized


def test_repairs_as_follows_merged_marker():
    agent = _build_agent()
    sample = "NOW This Deed Witnesseth as followsa. To pay rent"

    normalized = agent._normalize_generated_document(sample)

    assert "as follows:\na. To pay rent" in normalized
