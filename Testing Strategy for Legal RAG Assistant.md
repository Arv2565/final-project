# Testing Strategy for Legal RAG Assistant
This plan covers a layered testing approach to verify the correctness, quality, and reliability of the dual-retrieval legal RAG system — from unit-level logic through end-to-end response evaluation.
## Current State
* **Existing tests** cover only a small slice: AmbiguityRemover unit tests, vector retrieval integration tests, enrichment, hierarchy models, and a few verification scripts.
* **No tests exist** for: agent output quality, workflow routing correctness, end-to-end response verification, retrieval relevance, response grounding/accuracy, or LLM-as-judge evaluation.
* All agents use LLM calls via `get_agent_llm()` and return Pydantic-validated structured output — this is highly mockable.
## Layer 1: Unit Tests (No External Services)
These run fast with no LLM/DB dependencies. Use `unittest.mock` or `pytest` fixtures.
### 1a. Pydantic Model Validation
File: `tests/unit/test_models.py`
* `QueryRouterOutput` — verify `cleaned_query` required, `metadata.language` defaults
* `IntentClassifierOutput` — verify all `IntentType` enum values parse, `ExtractedEntities` optional fields
* `OrchestratorPlan` — verify `agent_number` validator rejects out-of-range (< 0, > 6), `legal_domain` literal enforcement
* `NextModule` — verify `agent_number` range 0–6
* `AgentType.from_number()` / `to_number()` round-trip
* `ActivityLawState` accumulation — build state step-by-step, verify `Optional` fields
* `ClarificationRequest` — verify `clarification_id` auto-generation, `dict()` serialization
### 1b. Routing Logic
File: `tests/unit/test_routing.py`
* Test `route_from_orchestrator()` directly with synthetic `GraphState` dicts:
    * agent_number=1 → `"fact_structuring"`
    * agent_number=2 + legal_domain="civil" → `"procedural_guidance_civil"`
    * agent_number=2 + legal_domain="criminal" → `"procedural_guidance_criminal"`
    * agent_number=3 (draft_builder) → `"doc_gen_template_selection"` (remapped)
    * agent_number=0 → `"general_chat"`
    * Missing `orchestrator_plan` → `END`
    * `pending_clarification` set → `END`
* Test `route_from_fact_structuring()`:
    * `ambiguity_remover_scope` set → `"ambiguity_remover"`
    * `pending_clarification` set → `END`
    * Default → `"statute_matching"`
* Test `route_from_ambiguity_remover()` and `route_from_doc_gen_clarification()`
### 1c. Entity Resolution & Parsing
File: `tests/unit/test_entity_utils.py`
* Entity parser: IPC sections, act names, jurisdiction extraction
* Entity resolver: canonical ID generation, deduplication of "Sec 420" vs "Section 420 IPC"
### 1d. Cypher Query Builders
Already partially covered in `tests/integration/test_vector_retrieval.py`. Add:
* `build_hybrid_vector_graph_query` with edge cases (empty relation_types, hops=0)
* Query validation with malformed inputs
## Layer 2: Agent-Level Tests (Mock LLM)
Mock the LLM to return deterministic Pydantic objects. Tests verify agents transform state correctly.
### 2a. QueryRouterAgent
File: `tests/unit/test_query_router_agent.py`
* Mock `get_agent_llm()` to return a fake LLM that returns `QueryRouterOutput`
* Test: Hindi input → cleaned English output
* Test: Missing `user_query` → raises `ValueError`
* Test: LLM failure → fallback `QueryRouterOutput` with original query
### 2b. IntentClassifierAgent
File: `tests/unit/test_intent_classifier_agent.py`
* Mock LLM returns `IntentClassifierOutput` with known intent
* Test: Missing `router_output` → raises `ValueError`
* Test: LLM failure → fallback to `GENERAL_QUESTION`
* Test: Verify all 8 `IntentType` values produce valid output
### 2c. OrchestratorAgent
File: `tests/unit/test_orchestrator_agent.py`
* Mock LLM returns `OrchestratorPlan` with specific `next_module`
* Test: Clarification flow — mock returns `clarification` field, verify `pending_clarification` in output
* Test: Max clarification limit (count=3) — verify forced best-guess
* Test: LLM failure → propagates exception (current behavior)
### 2d. Activity-to-Law Pipeline Agents
File: `tests/unit/test_activity_law_agents.py`
* Mock each of the 5 agents (FactStructuring, StatuteMatching, RuleMatching, RiskAssessment, EvidenceLinking)
* Test `ActivityToLawWorkflow.__call__()` with all agents mocked — verify state accumulation
* Test partial failure (one agent returns None) — verify workflow continues
### 2e. GeneralChatAgent
File: `tests/unit/test_general_chat_agent.py`
* Mock LLM returns `GeneralChatOutput`
* Test: LLM failure → fallback "I am a legal assistant" response
## Layer 3: Retrieval Quality Tests
These require either live services or substantial mocking.
### 3a. Vector Retrieval (Qdrant)
File: `tests/integration/test_qdrant_retrieval.py`
Mark with `@pytest.mark.integration` (skip if Qdrant unavailable).
* Ingest a small known corpus (3–5 legal text chunks) into a test collection
* Query with known terms → verify top-1 result matches expected chunk
* Query with unrelated terms → verify low scores
* Verify `RetrievalResult` structure: `retrieval_type="naive"`, `total_results > 0`
### 3b. Graph Retrieval (Neo4j)
File: `tests/integration/test_neo4j_retrieval.py`
Mark with `@pytest.mark.integration`.
* Seed test entities + relationships into a test Neo4j database
* Test `expand_entity_neighbors()` returns correct semantic + structural connections
* Test `_fetch_context_chunks()` returns linked chunks
* Test `health_check()` returns correct structure
### 3c. Hybrid Retrieval
File: `tests/unit/test_hybrid_retrieval.py`
* Mock both `QdrantVectorRetriever` and `Neo4jGraphRetriever`
* Verify weighted score calculation: vector_score * vector_weight, graph rank * graph_weight
* Verify deduplication and top_k limiting
* Test `set_vector_weight()` / `set_graph_weight()` — verify complementary weights (sum=1)
* Test graceful degradation: one backend fails → results from other still returned
* Test `is_available()` returns False when one backend is down
## Layer 4: Workflow Integration Tests (Mock LLM, Real Graph)
File: `tests/integration/test_workflow_e2e.py`
These test the full LangGraph pipeline with mocked LLMs but real graph execution.
### 4a. Happy Path Routes
Mock all agent LLMs with deterministic outputs. Verify:
* Activity query → goes through fact_structuring → statute_matching → rule_matching → risk_assessment → evidence_linking → response_generation → `final_response` populated
* Procedural query → goes to `procedural_guidance_civil` or `_criminal` → `final_response` populated
* General chat → goes to `general_chat` → `final_response` populated
* Doc gen query → template_selection → placeholder_extraction → clarification → document_creation → procedure_generation
### 4b. Clarification Loop
* Orchestrator returns clarification → verify `pending_clarification` in output, graph halts at `END`
* Resume with `clarification_history` → orchestrator now picks a module
* Verify max clarification limit enforcement (5 iterations in `app.py`)
### 4c. Error Resilience
* One node raises exception → verify graph doesn't crash (agents have try/except with fallbacks)
* Missing `router_output` reaching orchestrator → verify ValueError raised
## Layer 5: Response Quality Evaluation (Requires LLM)
This layer verifies the *quality* of LLM-generated responses. Use a separate evaluation LLM or the same provider.
### 5a. Golden Dataset
File: `tests/evaluation/golden_dataset.json`
Create 15–25 test cases across query types:
* 5 activity-to-law queries (e.g., "My landlord is refusing to return deposit", "Someone stole my phone")
* 5 procedural queries (e.g., "How to file an FIR?", "Steps for filing a consumer complaint")
* 3 document generation queries (e.g., "Draft a rental agreement")
* 3 general chat queries (e.g., "Hello", "What can you do?")
* 2 ambiguous queries that should trigger clarification
* 2 non-legal queries
Each case includes:
* `query`: input string
* `expected_route`: which agent should handle it (agent_number)
* `expected_domain`: civil/criminal
* `must_contain`: list of keywords/concepts the response must reference
* `must_not_contain`: things that indicate hallucination (wrong sections, fabricated cases)
### 5b. Automated Evaluation Script
File: `tests/evaluation/evaluate_responses.py`
Run the full pipeline against golden dataset and score each response on:
1. **Routing Accuracy** — Did orchestrator pick the correct agent? (deterministic check)
2. **Factual Grounding** — Does the response reference real statutes/provisions from the knowledge base? (keyword match against known corpus)
3. **Relevance** — Is the response topically relevant to the query? (embedding similarity between query and response, threshold > 0.7)
4. **Completeness** — Does the response address the key aspects of the query? (check `must_contain` keywords)
5. **Hallucination Check** — Does the response contain `must_not_contain` items? (keyword scan)
6. **Structure** — For activity-law responses: are factors, statutes, rules, risks, and evidence all populated?
Score each dimension 0–1, produce a summary report.
### 5c. LLM-as-Judge (Optional, Higher Cost)
File: `tests/evaluation/llm_judge.py`
Use a separate LLM (e.g., GPT-4o) to evaluate responses:
* Prompt: "Given this legal query and the system's response, rate on a 1-5 scale for: accuracy, helpfulness, completeness, and safety."
* Store results in `tests/evaluation/results/` for trend tracking
* Run periodically (not on every CI push) due to cost
## Layer 6: Backend Integration Tests
File: `backend/tests/test_chat_service.py`
* Test `ChatService.process_query()` with mocked workflow → verify response structure
* Test WebSocket handler: send `{"type": "query", "payload": "..."}` → receive `final_result`
* Test clarification WebSocket flow: receive `clarification_request` → send `clarification_response` → receive `final_result`
* Test error handling: invalid message type, empty query
## Test Configuration
### Markers
```python
# conftest.py additions
pytest.ini or pyproject.toml:
[tool.pytest.ini_options]
markers = [
    "unit: fast tests with no external dependencies",
    "integration: requires Qdrant/Neo4j",
    "evaluation: runs golden dataset evaluation (slow, needs LLM)",
    "expensive: requires paid LLM API calls",
]
```
### Running
* `pytest tests/unit/` — fast, no deps (CI on every push)
* `pytest tests/integration/ -m integration` — needs Docker services
* `pytest tests/evaluation/ -m evaluation` — needs LLM API key, run weekly or on release
## Priority Order
1. **Layer 1b** (routing logic) — highest impact, zero cost, catches misrouting bugs
2. **Layer 2a–2c** (core agent tests) — verify the 3 core agents work with mocked LLMs
3. **Layer 5a** (golden dataset) — create the evaluation dataset
4. **Layer 5b** (evaluation script) — automated quality scoring
5. **Layer 3c** (hybrid retrieval) — verify retrieval blending logic
6. **Layer 4a–4c** (workflow integration) — full pipeline verification
7. **Layer 6** (backend) — WebSocket/API tests
8. **Layers 1a, 1c, 1d, 2d, 2e** — fill in remaining unit tests
9. **Layer 5c** (LLM judge) — optional, for ongoing quality tracking
