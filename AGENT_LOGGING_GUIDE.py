"""
=============================================================================
AGENT LOGGING GUIDE - TERMINAL OUTPUT DOCUMENTATION
=============================================================================

All 8 agents now print detailed logging to the terminal as they execute.
This guide explains what each log line means.

=============================================================================
LOGGING FORMAT FOR EACH AGENT
=============================================================================

Each agent follows this consistent logging pattern:

┌─────────────────────────────────────────────────────────────────────────┐
│ ════════════════════════════════════════════════════════════════════    │
│ 🔄 AGENT_NAME_WITH_EMOJI                                               │
│ ════════════════════════════════════════════════════════════════════    │
│                                                                          │
│ 📥 Input State:                                                        │
│    field_name: value_from_graph_state                                  │
│    another_field: another_value                                        │
│                                                                          │
│ [Processing... LLM call happens here]                                  │
│                                                                          │
│ ✅ Agent Output:                                                        │
│    result_field: value_produced_by_llm                                 │
│    another_result: another_output                                      │
│                                                                          │
│ 📤 Return: key_name_updated_in_state                                   │
│ ════════════════════════════════════════════════════════════════════    │
└─────────────────────────────────────────────────────────────────────────┘

=============================================================================
AGENT LOGGING DETAILS
=============================================================================

1️⃣  QUERY ROUTER AGENT 🔄
─────────────────────────────────────────────────────────────────────────
Purpose: Normalizes raw user query and extracts metadata
Logs:
  📥 Input State:
     user_query: The raw query from the user
  
  ✅ Router Output:
     Cleaned Query: The processed, normalized query
     Language: Detected language (en, hi, etc.)
     Has Personal Data: Whether PII was detected
     Is Legal Question: Whether it's actually a legal question
  
  📤 Return: router_output

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔄 QUERY ROUTER AGENT                                                   │
│ 📥 Input State:                                                        │
│    user_query: What is Section 420 of IPC?...                         │
│ ✅ Router Output:                                                       │
│    Cleaned Query: What is Section 420 of the Indian...                │
│    Language: en                                                        │
│    Has Personal Data: False                                           │
│    Is Legal Question: True                                            │
│ 📤 Return: router_output                                               │
└─────────────────────────────────────────────────────────────────────────┘


2️⃣  INTENT CLASSIFIER AGENT 🔍
─────────────────────────────────────────────────────────────────────────
Purpose: Classifies user intent and extracts entities
Logs:
  📥 Input State:
     Cleaned Query: From QueryRouter output
     Language: From QueryRouter metadata
  
  ✅ Classifier Output:
     Intent: ask_procedure | ask_law_explanation | ask_case_reference | etc.
     Jurisdiction: Identified jurisdiction (India, UK, etc.)
     Topic: Legal topic identified (divorce, fraud, etc.)
     Time Frame: Time-related entities
  
  📤 Return: classifier_output

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔍 INTENT CLASSIFIER AGENT                                              │
│ 📥 Input State:                                                        │
│    Cleaned Query: What is Section 420 of IPC...                       │
│    Language: en                                                        │
│ ✅ Classifier Output:                                                   │
│    Intent: ask_law_explanation                                        │
│    Jurisdiction: India                                                 │
│    Topic: Fraud                                                        │
│    Time Frame: None                                                    │
│ 📤 Return: classifier_output                                            │
└─────────────────────────────────────────────────────────────────────────┘


3️⃣  ORCHESTRATOR AGENT 🎯
─────────────────────────────────────────────────────────────────────────
Purpose: Routes query to appropriate specialized agents (1-6)
Logs:
  📥 Input State:
     Query: From QueryRouter output
     Intent: From IntentClassifier output
     Jurisdiction: Extracted entity
     Topic: Extracted entity
  
  ✅ Orchestrator Output:
     Planning Steps: List of agent numbers and descriptions
       - Agent 1: Activity-to-Law Pipeline (comprehensive analysis)
       - Agent 2-6: Other specialized agents based on intent
  
  📤 Return: orchestrator_plan

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ 🎯 ORCHESTRATOR AGENT                                                    │
│ 📥 Input State:                                                        │
│    Query: What is Section 420 of IPC...                               │
│    Intent: ask_law_explanation                                        │
│    Jurisdiction: India                                                 │
│    Topic: Fraud                                                        │
│ ✅ Orchestrator Output:                                                 │
│    Planning Steps:                                                     │
│       - Agent 1: Run Activity-to-Law pipeline for analysis             │
│ 📤 Return: orchestrator_plan                                            │
└─────────────────────────────────────────────────────────────────────────┘


4️⃣  FACT STRUCTURING AGENT 📋
─────────────────────────────────────────────────────────────────────────
Purpose: Structures facts and events from the query
Logs:
  📥 Input State:
     Query: The cleaned query to analyze
  
  ✅ Fact Structuring Output:
     Factors: N identified (contextual factors in the case)
     Events: N identified (timeline and events)
  
  📤 Return: fact_structuring

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ 📋 FACT STRUCTURING AGENT                                               │
│ 📥 Input State:                                                        │
│    Query: What is Section 420 of IPC...                               │
│ ✅ Fact Structuring Output:                                             │
│    Factors: 3 identified                                               │
│    Events: 2 identified                                                │
│ 📤 Return: fact_structuring                                             │
└─────────────────────────────────────────────────────────────────────────┘


5️⃣  STATUTE MATCHING AGENT ⚖️
─────────────────────────────────────────────────────────────────────────
Purpose: Matches applicable statutes/laws to the facts
Logs:
  📥 Input State:
     Factors: From fact structuring
     Events: From fact structuring
  
  ✅ Statute Matching Output:
     Candidate Statutes: N found (relevant legal statutes)
  
  📤 Return: statute_matching

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚖️  STATUTE MATCHING AGENT                                               │
│ 📥 Input State:                                                        │
│    Factors: 3 from fact structuring                                    │
│    Events: 2 from fact structuring                                     │
│ ✅ Statute Matching Output:                                             │
│    Candidate Statutes: 4 found                                         │
│ 📤 Return: statute_matching                                             │
└─────────────────────────────────────────────────────────────────────────┘


6️⃣  RULE MATCHING AGENT 📜
─────────────────────────────────────────────────────────────────────────
Purpose: Matches legal rules within identified statutes
Logs:
  📥 Input State:
     Candidate Statutes: From statute matching
     Factors: From fact structuring
     Events: From fact structuring
  
  ✅ Rule Matching Output:
     Rule Assessments: N created (legal rules applicable to facts)
  
  📤 Return: rule_matching

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ 📜 RULE MATCHING AGENT                                                   │
│ 📥 Input State:                                                        │
│    Candidate Statutes: 4                                               │
│    Factors: 3                                                          │
│    Events: 2                                                           │
│ ✅ Rule Matching Output:                                                │
│    Rule Assessments: 6 created                                         │
│ 📤 Return: rule_matching                                                │
└─────────────────────────────────────────────────────────────────────────┘


7️⃣  RISK ASSESSMENT AGENT ⭐ ⚠️
─────────────────────────────────────────────────────────────────────────
Purpose: Evaluates legal risk level for the situation
KEY AGENT - Produces critical risk assessment
Logs:
  📥 Input State:
     Rule Assessments: From rule matching
     Factors: From fact structuring
     Events: From fact structuring
  
  ✅ Risk Assessment Output:
     Risk Level: HIGH | MEDIUM | LOW (overall risk)
     Risk Matrix: Available with severity levels for each factor
  
  📤 Return: risk_assessment

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚠️  RISK ASSESSMENT AGENT ⭐                                             │
│ 📥 Input State:                                                        │
│    Rule Assessments: 6 to evaluate                                     │
│    Factors: 3                                                          │
│    Events: 2                                                           │
│ ✅ Risk Assessment Output:                                              │
│    Risk Level: HIGH                                                    │
│    Risk Matrix: Available with severity levels                         │
│ 📤 Return: risk_assessment                                              │
└─────────────────────────────────────────────────────────────────────────┘


8️⃣  EVIDENCE LINKING AGENT 🔗
─────────────────────────────────────────────────────────────────────────
Purpose: Links evidence to findings and creates final report
Logs:
  📥 Input State:
     Risk Matrix: From risk assessment
     Factors: From fact structuring
     Events: From fact structuring
  
  ✅ Evidence Linking Output:
     Linked Evidence: N connections made (evidence linked to findings)
  
  📤 Return: evidence_linking

Example Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔗 EVIDENCE LINKING AGENT                                               │
│ 📥 Input State:                                                        │
│    Risk Matrix: Available from risk assessment                         │
│    Factors: 3                                                          │
│    Events: 2                                                           │
│ ✅ Evidence Linking Output:                                             │
│    Linked Evidence: 8 connections made                                 │
│ 📤 Return: evidence_linking                                             │
└─────────────────────────────────────────────────────────────────────────┘

=============================================================================
DATA FLOW VISUALIZATION
=============================================================================

Input Query
    ↓
🔄 QueryRouterAgent
    ├─ 📥 Input: user_query
    ├─ ✅ Output: router_output
    └─ 📤 Return: router_output
    ↓
🔍 IntentClassifierAgent
    ├─ 📥 Input: router_output
    ├─ ✅ Output: classifier_output
    └─ 📤 Return: classifier_output
    ↓
🎯 OrchestratorAgent
    ├─ 📥 Input: router_output, classifier_output
    ├─ ✅ Output: orchestrator_plan
    └─ 📤 Return: orchestrator_plan
    ↓
[CONDITIONAL ROUTING: If Agent 1 selected]
    ↓
📋 FactStructuringAgent
    ├─ 📥 Input: router_output.cleaned_query
    ├─ ✅ Output: factors, events
    └─ 📤 Return: fact_structuring
    ↓
⚖️  StatuteMatchingAgent
    ├─ 📥 Input: factors, events
    ├─ ✅ Output: candidate_statutes
    └─ 📤 Return: statute_matching
    ↓
📜 RuleMatchingAgent
    ├─ 📥 Input: candidate_statutes, factors, events
    ├─ ✅ Output: rule_assessments
    └─ 📤 Return: rule_matching
    ↓
⚠️  RiskAssessmentAgent ⭐
    ├─ 📥 Input: rule_assessments, factors, events
    ├─ ✅ Output: risk_level, risk_matrix
    └─ 📤 Return: risk_assessment
    ↓
🔗 EvidenceLinkingAgent
    ├─ 📥 Input: risk_matrix, factors, events
    ├─ ✅ Output: linked_evidence
    └─ 📤 Return: evidence_linking
    ↓
Final Result

=============================================================================
ERROR HANDLING LOGS
=============================================================================

When an agent fails (e.g., API quota exceeded), you'll see:

⚠️  Agent_Name failed, using fallback: [Error message truncated to 100 chars]

This indicates:
- The LLM call failed (usually due to API errors, quota limits, etc.)
- The agent is using a fallback/default output
- The workflow continues with default values instead of LLM output
- Check .env and API credentials if errors persist

Example Error Log:
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔄 QUERY ROUTER AGENT                                                    │
│ 📥 Input State:                                                        │
│    user_query: What is Section 420 of IPC?...                         │
│ ⚠️  Router failed, using fallback: Error calling model 'gemini-2.0-    │
│    flash' (RESOURCE_EXHAUSTED): 429 API quota limit exceeded...        │
│ [Fallback: Returns original query with default metadata]               │
└─────────────────────────────────────────────────────────────────────────┘

=============================================================================
RUNNING TESTS WITH LOGGING
=============================================================================

To see all agent logs in action, run:

    python examples/test_agent_logging.py

This will execute the full pipeline and show:
1. All agent headers with emojis
2. Input state from graph for each agent
3. Processing output from LLM
4. Return values updating graph state
5. Final state summary

=============================================================================
TROUBLESHOOTING WITH LOGS
=============================================================================

Use the logs to debug issues:

1. Agent Not Running?
   - Check if previous agent completed (look for 📤 Return line)
   - Look for ⚠️  error messages
   - Check if agent returned None

2. Wrong Output?
   - Look at 📥 Input State - is the previous agent's output correct?
   - Look at ✅ Output - does it match expected structure?
   - Check temperature settings in .env

3. Data Not Flowing?
   - Verify 📤 Return key matches what next agent expects
   - Check GraphState type definitions in src/models/

4. API Errors?
   - Look for ⚠️  RESOURCE_EXHAUSTED or timeout messages
   - Check GEMINI_API_KEY and rate limits
   - Can switch to OpenAI provider via .env

=============================================================================

For more details, see: GEMINI_INTEGRATION_SUMMARY.py

=============================================================================
"""

if __name__ == "__main__":
    print(__doc__)
