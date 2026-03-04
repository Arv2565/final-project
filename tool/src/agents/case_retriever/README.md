"""
CASE RETRIEVAL MODULE - IMPLEMENTATION COMPLETE

This comprehensive guide documents the Case Retrieval Module for the Legal RAG Assistant.
The module retrieves relevant cases by court level, detects appellate chains, identifies
reversals, and synthesizes findings into actionable legal recommendations.

================================================================================
TABLE OF CONTENTS
================================================================================
1. Architecture Overview
2. Module Components
3. Data Flow & Processing
4. Setup & Ingestion
5. Usage Examples
6. API Reference
7. Database Schema
8. Chunking Strategy & Metadata

================================================================================
1. ARCHITECTURE OVERVIEW
================================================================================

The Case Retrieval Module is a **three-agent system** with **independent Qdrant + Neo4j**
graph for maximum flexibility:

    User Query (from Orchestrator)
           ↓
    ┌──────────────────────────────────────────────┐
    │  CASE RETRIEVER WORKFLOW                     │
    │  (tool/src/agents/case_retriever/workflow.py) │
    └──────────────────────────────────────────────┘
           ↓
    ┌───────────────────────────┬──────────────────────┐
    ▼                           ▼
    ┌─────────────────────┐  ┌─────────────────────┐
    │ LOWER COURT FINDER  │  │ UPPER COURT FINDER  │  ← Parallel Execution
    │ (Agent 1)           │  │ (Agent 2)           │
    │                     │  │                     │
    │ • District Courts   │  │ • Supreme Court     │
    │ • Trial Courts      │  │ • High Courts       │
    │ • Recent cases      │  │ • Precedents        │
    │ • Vector search     │  │ • Appellate chains  │
    └─────────────────────┘  └─────────────────────┘
           ↓                           ↓
           └───────────────┬───────────┘
                          ▼
    ┌──────────────────────────────────────┐
    │ COMPARATIVE ANALYZER (Agent 3)       │
    │                                      │
    │ • Finds common statutes              │
    │ • Identifies reversals               │
    │ • Derives legal principles           │
    │ • Generates recommendations          │
    └──────────────────────────────────────┘
           ↓
    STRUCTURED CASE ANALYSIS RESULT
    (CaseAnalysisResult model)

================================================================================
2. MODULE COMPONENTS
================================================================================

Directory Structure:

  tool/
  ├── src/
  │   ├── utils/
  │   │   ├── court_hierarchy.py          # Court level classification
  │   │   └── case_relationships.py       # Appellate relationship inference
  │   │
  │   ├── database/
  │   │   ├── qdrant/
  │   │   │   └── case_collection.py      # Case collection manager
  │   │   └── neo4j/
  │   │       └── case_schema.py          # Case graph schema
  │   │
  │   ├── retrieval/
  │   │   └── case.py                     # Case-specific retrievers
  │   │
  │   ├── agents/
  │   │   └── case_retriever/
  │   │       ├── models.py               # Pydantic models
  │   │       ├── lower_court_finder.py   # Agent 1
  │   │       ├── upper_court_finder.py   # Agent 2
  │   │       ├── comparative_analyzer.py # Agent 3
  │   │       ├── workflow.py             # Orchestrator
  │   │       └── __init__.py
  │   │
  │   └── nodes/
  │       └── case_retriever_node.py      # LangGraph node wrapper
  │
  ├── pipelines/
  │   └── document_ingestion/
  │       └── case_ingester.py            # Ingestion pipeline
  │
  └── scripts/
      └── ingest_cases.py                 # CLI for ingestion


Key Classes & Functions:

UTILITIES:
  • CourtLevel (Enum): Court hierarchy levels (1-3)
  • get_court_level(name, text): Determine court level
  • infer_case_hierarchy(): Detect appellate relationships
  • detect_reversal_status(): Find case overturns

DATABASE MANAGERS:
  • QdrantCaseCollectionManager: Manages legal_cases collection
  • CaseGraphSchema: Neo4j graph for cases and relationships

RETRIEVERS:
  • LowerCourtCaseRetriever: Vector search for lower courts
  • UpperCourtCaseRetriever: Vector + graph search for precedents
  • CaseAppellateChainRetriever: Graph traversal for appeals

AGENTS:
  • LowerCourtCaseFinderAgent: Finds lower court cases
  • UpperCourtCaseFinderAgent: Finds precedents & chains
  • CaseComparativeAnalyzerAgent: Synthesizes & analyzes
  • CaseRetrieverWorkflow: Orchestrates all three

MODELS (Pydantic):
  • CaseInfo: Single case metadata
  • LowerCourtCaseResult: Lower finder output
  • UpperCourtCaseResult: Upper finder output
  • CaseAnalysisResult: Final synthesized output

================================================================================
3. DATA FLOW & PROCESSING
================================================================================

INPUT → CASEFILES.JSON

  Each case record contains:
  {
    "metadata": {
      "court": "Supreme Court of India",
      "bench": ["J. Name 1", "J. Name 2"],
      "date": "YYYY-MM-DD",
      "citation": "[YYYY] X SCC Y",
      "language": "en"
    },
    "issues": [
      {
        "issue_id": "issue_type",
        "natural_form": "Question posed...",
        "legal_domain": "criminal_law",
        "outcome": "allowed|denied|clarified"
      }
    ],
    "ratio": {
      "text": "Full reasoning text...",
      "summary": "Optional abbreviated version"
    },
    "statutes_interpreted": [
      {
        "statute_name": "Legal Act Name",
        "section": "Section #",
        "interpretation": "How interpreted..."
      }
    ],
    "holding": {
      "decision": "appeal_allowed|dismissed|...",
      "relief": "Specific orders granted..."
    },
    "legal_concepts": ["tag1", "tag2", ...],
    "evidence": {
      "pdf_path": "tool/data/case_files/...",
      "relevant_page_ranges": ["X-Y"]
    }
  }


PROCESSING PIPELINE:

  1. READ & VALIDATE
     ↓
  2. COMPUTE COURT LEVELS
     ↓
  3. SEMANTIC CHUNKING (4 types)
     • Issue chunks (law, concepts, outcome)
     • Ratio chunks (reasoning, analysis)
     • Statute chunks (interpretations)
     • Holding chunks (decision, relief)
     ↓
  4. GENERATE EMBEDDINGS (inLegalBERT 768-dim)
     ↓
  5. STORE IN QDRANT
     • Collection: legal_cases
     • Vector + Metadata indexing
     ↓
  6. CREATE NEO4J NODES
     • Case, Issue, Statute, Judge nodes
     • RAISES, INTERPRETS, DECIDED_BY relations
     ↓
  7. INFER APPELLATE RELATIONSHIPS
     • Parse citations
     • Detect reversal keywords
     • Create APPEALS_FROM, CITES relations


INGESTION COMMAND:

  # Basic ingestion
  python tool/scripts/ingest_cases.py --source tool/data/casefiles.json

  # Clear collections first
  python tool/scripts/ingest_cases.py --source tool/data/casefiles.json --refresh

  # Test with sample
  python tool/scripts/ingest_cases.py --source tool/data/casefiles.json --sample 5

  # Verbose logging
  python tool/scripts/ingest_cases.py --source tool/data/casefiles.json --verbose


================================================================================
4. SETUP & INGESTION
================================================================================

PREREQUISITES:
  1. Qdrant running on configured host:port
  2. Neo4j running on configured URI
  3. inLegalBERT model available (downloads automatically)
  4. tool/data/casefiles.json present

ENVIRONMENT VARIABLES (in .env or settings):
  QDRANT_HOST=localhost
  QDRANT_PORT=6333
  QDRANT_API_KEY=<optional>
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=<your_password>

INGESTION STEPS:

  $ cd /Users/pranav/Documents/Projects/final-project

  # 1. Verify databases are running
  $ curl http://localhost:6333/health  # Qdrant
  $ neo4j-admin check-consistency      # Neo4j

  # 2. Run ingestion
  $ python tool/scripts/ingest_cases.py --source tool/data/casefiles.json --verbose

  # 3. Monitor progress
  [Output shows cases processed, chunks created, embeddings generated]

  # 4. Verify in Qdrant
  $ curl http://localhost:6333/collections/legal_cases

  # 5. Verify in Neo4j
  $ MATCH (c:Case) RETURN count(c) as total_cases;


================================================================================
5. USAGE EXAMPLES
================================================================================

EXAMPLE 1: Case Retrieval via Chat Interface

  User: "What are the leading cases on Article 21 (personal liberty)?"

  → Orchestrator routes to agent 5 (case_retriever)
  → LowerCourtCaseFinderAgent searches for lower court cases on Article 21
  → UpperCourtCaseFinderAgent finds Supreme Court precedents
  → CaseComparativeAnalyzerAgent synthesizes and identifies principles
  → Returns: List of cases with precedent chains, key rulings, recommendations


EXAMPLE 2: Reversal Pattern Detection

  User: "Show me cases on Section 302 (murder) that were overturned in appeal"

  → Query concepts: ["overturned", "appeal", "section 302"]
  → LowerCourtCaseFinderAgent: 8 lower court Section 302 cases found
  → UpperCourtCaseFinderAgent: Queries Neo4j for APPEALS_FROM reversed cases
  → CaseComparativeAnalyzerAgent: "3 cases identified with reversals"
  → Output: Details of reversals, why overturned, legal implications


EXAMPLE 3: Direct API Usage (Python)

  from src.agents.case_retriever.workflow import CaseRetrieverWorkflow

  workflow = CaseRetrieverWorkflow()
  result = workflow(
      state={"user_query": "Cases on habeas corpus from Kerala High Court"},
      callbacks=None
  )

  analysis = result["analysis_result"]
  print(f"Found {len(analysis.lower_court_cases)} lower court cases")
  print(f"Found {len(analysis.precedents)} precedents")
  print(f"Confidence: {analysis.confidence_score:.0%}")


EXAMPLE 4: Direct Retriever Usage

  from src.retrieval.case import LowerCourtCaseRetriever, UpperCourtCaseRetriever

  # Lower court search
  lower_retriever = LowerCourtCaseRetriever()
  lower_result = lower_retriever.retrieve(
      query="custody torture cases",
      top_k=10,
      legal_domain="criminal_law"
  )

  # Upper court search
  upper_retriever = UpperCourtCaseRetriever()
  upper_result = upper_retriever.retrieve(
      query="custody torture cases",
      find_precedents=True
  )


================================================================================
6. API REFERENCE
================================================================================

MODELS:

CaseInfo
  • case_id: str
  • citation: str (e.g., "(2000) 6 SCC 359")
  • court: str (e.g., "Supreme Court of India")
  • court_level: int (1=Supreme, 2=High, 3=Lower)
  • date: str (ISO format)
  • decision: Optional[str]
  • parties_appellant: Optional[str]
  • parties_respondent: Optional[str]
  • legal_concepts: List[str]
  • statutes_mentioned: List[str]
  • similarity_score: Optional[float]

LowerCourtCaseResult
  • cases: List[CaseInfo]
  • query_concepts: List[str]
  • search_query: str
  • retrieval_confidence: float (0.0-1.0)
  • total_cases_available: int
  • filters_applied: Dict

UpperCourtCaseResult
  • precedents: List[PrecedentInfo]
  • appellate_chains: List[List[AppellateChainLink]]
  • query_concepts: List[str]
  • retrieval_confidence: float
  • total_precedents_available: int
  • reversals_detected: int

CaseAnalysisResult (FINAL OUTPUT)
  • summary: str (narrative analysis)
  • lower_court_cases: List[CaseInfo]
  • precedents: List[PrecedentInfo]
  • common_statutes: List[CommonStatuteInfo]
  • appellate_chains: List[List[AppellateChainLink]]
  • reversals_identified: List[Dict] (with reversal details)
  • legal_principles_derived: List[str] (key principles)
  • confidence_score: float (overall confidence)
  • recommendations: str (actionable next steps)


DATABASE METHODS:

QdrantCaseCollectionManager:
  • store_case_chunks(case_vectors) → int
  • search_cases(query_embedding, top_k, filters) → List[Dict]
  • get_cases_by_court_level(levels, date_range, domain) → List[Dict]
  • get_collection_stats() → Dict

CaseGraphSchema:
  • create_case_node(...) → bool
  • create_issue_node(...) → bool
  • create_statute_node(...) → bool
  • create_judge_node(...) → bool
  • create_relationship(...) → bool
  • query_case_precedents(case_id, depth) → List[Dict]
  • query_appellate_chain(case_id) → List[Dict]
  • query_cases_by_statute(statute_name, section) → List[Dict]


================================================================================
7. DATABASE SCHEMA
================================================================================

QDRANT COLLECTION: legal_cases

  Vector Size: 768 (inLegalBERT)
  Distance Metric: Cosine Similarity
  Point ID: UUID-based (numeric for storage)

  Indexed Metadata Fields:
    • case_id (KEYWORD)
    • citation (KEYWORD)
    • court (KEYWORD)
    • court_level (INTEGER) - 1=Supreme, 2=High, 3=Lower
    • date (KEYWORD) - ISO format for range queries
    • year (INTEGER)
    • case_type (KEYWORD) - Criminal, Civil, Constitutional
    • content_type (KEYWORD) - issue|ratio|statute|holding
    • legal_domain (KEYWORD) - criminal_law, civil_law, etc.
    • legal_concepts (KEYWORD array)
    • statutes_mentioned (KEYWORD array)
    • decision (KEYWORD)
    • relief_type (KEYWORD)
    • parties_appellant (KEYWORD)
    • parties_respondent (KEYWORD)

  Example Payload:
  {
    "case_id": "(2021)_3_S.C.R._576",
    "content_type": "issue",
    "chunk_text": "Whether the Act mandates reservation in promotion...",
    "citation": "[2021] 3 S.C.R. 576",
    "court": "Supreme Court of India",
    "court_level": 1,
    "date": "2021-06-28",
    "year": 2021,
    "legal_concepts": ["reservation_in_promotion", "persons_with_disabilities"],
    "statutes_mentioned": ["Persons with Disabilities Act, 1995"],
  }


NEO4J GRAPH SCHEMA:

  Nodes:
    :Case {
      case_id: String (UNIQUE),
      citation: String (UNIQUE),
      date: String (ISO format),
      court: String,
      court_level: Integer,
      case_type: String,
      parties_appellant: String,
      parties_respondent: String,
      decision: String,
      relief: String,
      has_reversal: Boolean,
      year: Integer,
      created_at: DateTime
    }

    :CaseIssue {
      issue_id: String (UNIQUE),
      description: String,
      legal_domain: String,
      outcome: String,
      created_at: DateTime
    }

    :CaseStatute {
      statute_name: String,
      section: String,
      interpretation_summary: String,
      created_at: DateTime
    }

    :CaseJudge {
      name: String (UNIQUE),
      court: String (Optional),
      created_at: DateTime
    }

  Relationships:
    :Case -[:RAISES]-> :CaseIssue
    :Case -[:INTERPRETS {date: String, section: String}]-> :CaseStatute
    :Case -[:DECIDED_BY]-> :CaseJudge
    :Case -[:CITES {confidence: Float}]-> :Case (precedent)
    :Case -[:APPEALS_FROM {reversal_status: UPHELD|REVERSED|MODIFIED|REMANDED}]-> :Case
    :Case -[:REMANDED_TO]-> :Case

  Constraints:
    • case_id UNIQUE
    • citation UNIQUE
    • judge name UNIQUE

  Indexes:
    • case_date
    • case_court
    • case_court_level
    • statute_name
    • statute_section


================================================================================
8. CHUNKING STRATEGY & METADATA
================================================================================

SEMANTIC-AWARE CHUNKING (NOT token-based):

The module chunks cases by LEGAL MEANING, not arbitrary token counts.

Chunk Type 1: ISSUE
  Content: Legal question posed, outcome
  Size: 300-500 tokens
  Metadata: issue_id, outcome, legal_domain
  Use: Identify what question the case answers

Chunk Type 2: RATIO (Reasoning)
  Content: Court's legal reasoning and analysis
  Size: 400-600 tokens
  Metadata: key_concepts, statute_references, reasoning_type
  Use: Core precedent value

Chunk Type 3: STATUTE INTERPRETATION
  Content: Statute name + section + how interpreted
  Size: 200-400 tokens
  Metadata: statute_name, section, interpretation_date
  Use: Statutory construction guidance

Chunk Type 4: HOLDING (Decision)
  Content: Court's decision, relief granted
  Size: 300-500 tokens
  Metadata: decision_type, relief_type, reversal_indicators
  Use: Outcome/precedent value


METADATA USAGE:

Filter queries by multiple dimensions:
  • Court level (Supreme → High → Lower)
  • Date range (post-2015 cases only)
  • Legal domain (criminal_law, service_law, etc.)
  • Statute (specific sections)
  • Concepts (personal_liberty, bail, etc.)

Example filter:
  {
    "court_level": {"in": [1, 2]},  // Supreme or High Court
    "date": {"gte": "2020-01-01"},
    "legal_domain": {"eq": "criminal_law"},
    "legal_concepts": {"contains": "bail"}
  }


EMBEDDING CONSISTENCY:

  • All chunks use inLegalBERT (768 dimensions)
  • Max sequence length: 512 tokens → Safe max chunk: 450 tokens
  • Overlap: 50 tokens between chunks (context preservation)
  • Min chunk size: 100 tokens (skip too-small fragments)


================================================================================
CONFIGURATION & MONITORING
================================================================================

To enable detailed logging:
  import logging
  logging.getLogger("src.agents.case_retriever").setLevel(logging.DEBUG)

To monitor Qdrant collection:
  $ curl http://localhost:6333/collections/legal_cases

To monitor Neo4j:
  $ cypher-shell "MATCH (c:Case) RETURN count(*) as total;"
  $ cypher-shell "MATCH ()-[r:APPEALS_FROM]->() RETURN count(r) as reversals;"


TO TEST THE FULL WORKFLOW:

  python -c "
  from src.agents.case_retriever.workflow import CaseRetrieverWorkflow
  workflow = CaseRetrieverWorkflow()
  result = workflow({'user_query': 'habeas corpus Supreme Court'})
  print(f'Completed: {result[\"case_retriever_state\"][\"workflow_status\"]}'
  "

================================================================================
NOTES FOR FUTURE ENHANCEMENT
================================================================================

1. **Appellate Chain Inference**: Currently uses text patterns. Could use
   coreference resolution + entity linking to more accurately match lower court
   cases to their appeals.

2. **Cross-Statute Linking**: Extend Neo4j to link statutes (e.g., "IPC Section
   420 is amended by BNS Section 318") for better relationship mapping.

3. **LLM-Enhanced Query Extraction**: Replace simple keyword extraction with
   LLM-based query understanding to extract legal concepts, statutes, court
   preferences, and date ranges more accurately.

4. **Similarity Re-ranking**: Use LLM to re-rank vector search results based on
   semantic relevance, not just embedding similarity.

5. **Batch Historical Analysis**: Run appellate chain reconstruction over entire
   dataset to populate APPEALS_FROM relationships more comprehensively.

6. **Explicit Reversal Database**: Create a separate Neo4j construct explicitly
   mapping lower court decisions to their reversals (currently inferred).

================================================================================
Module Implementation Status: COMPLETE ✓
Ready for: Integration Testing, Data Ingestion, User Feedback
================================================================================
"""

# This file serves as documentation. Execute this as needed for reference.
if __name__ == "__main__":
    print(__doc__)
