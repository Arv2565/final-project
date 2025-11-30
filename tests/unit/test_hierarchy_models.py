import pytest
from models.extracted_entity import ExtractedEntity
from models.legal_document_v2 import LegalDocumentKnowledgeV2

from workflows.graphs.graph_rag_indexer import Triple


def test_extracted_entity_model():
    e = ExtractedEntity(
        name="Section 420",
        entity_type="Section",
        canonical_id="IPC:Section:420",
        parent_id="IPC:Chapter:XVII",
        hierarchy_level=3,
        source="IPC",
        confidence=1.0,
    )
    assert e.name == "Section 420"
    assert e.canonical_id.startswith("IPC:Section")


def test_legal_document_v2_entities():
    doc = LegalDocumentKnowledgeV2(
        title="IPC Sample",
        purpose="Sample",
        scope="India",
        key_provisions=["Section 420: Cheating", "Section 415: Cheating definition", "Section 493: Adultery", "Section 302: Murder"],
        administration="Govt",
        entities=[
            {"name": "Section 420", "entity_type": "Section", "canonical_id": "IPC:Section:420"}
        ]
    )
    assert doc.entities is not None
    assert len(doc.entities) >= 1


def test_triple_model_canonical_fields():
    t = Triple(
        head="Section 420",
        relation="part_of",
        tail="Chapter XVII",
        head_type="Section",
        tail_type="Chapter",
        relation_confidence=0.95,
        head_canonical_id="IPC:Section:420",
        tail_canonical_id="IPC:Chapter:XVII",
    )
    assert t.head_canonical_id == "IPC:Section:420"
    assert t.tail_canonical_id == "IPC:Chapter:XVII"
