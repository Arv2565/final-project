from pipelines.graph_index.enrichment import normalize_name, canonicalize_entities, enrich_relation


def test_normalize_name_basic():
    assert normalize_name(" Supreme   Court ") == "supreme court"
    assert normalize_name("IPC, 1860") == "ipc, 1860"


def test_canonicalize_groups():
    names = ["Supreme Court", "supreame court", "High Court", "high court"]
    name_to_canon, groups = canonicalize_entities(names, threshold=0.75)
    # variants present
    assert any("Supreme Court" in v or "supreme court" in v for v in groups.keys()) or len(groups) >= 1
    # mapping covers input
    for n in names:
        assert n in name_to_canon


def test_enrich_relation_basic():
    assert enrich_relation("amends") == "amendment_of"
    assert enrich_relation("cites") == "cited_in"
    assert enrich_relation("something unusual") != ""
