from src.agents.comparative_module_agent import ComparativeModuleAgent


def test_comparative_service_uses_precomputed_table_for_known_topic():
    service = ComparativeModuleAgent()

    result = service.run("Compare Kerala and Karnataka lottery law")

    assert result["comparison_mode"] == "precomputed"
    assert result["comparison_match_id"] == "lottery_002"
    assert "| Aspect | Kerala | Karnataka |" in result["final_response"]
    assert "In summary" in result["final_response"]


def test_comparative_service_falls_back_for_unknown_topic():
    service = ComparativeModuleAgent()

    result = service.run("Compare Kerala and Karnataka drone policy")

    assert result["comparison_mode"] == "fallback"
    assert result["comparison_match_id"] is None
    assert "| Aspect |" in result["final_response"]
    assert "In conclusion" in result["final_response"]


def test_comparative_service_requests_clarification_when_states_missing():
    service = ComparativeModuleAgent()

    result = service.run("Compare lottery law")

    assert result["comparison_mode"] == "clarification"
    assert result["needs_clarification"] is True
    assert "pending_clarification" in result
    assert "question" in result["pending_clarification"]
