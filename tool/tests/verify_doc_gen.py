import asyncio
import logging
from src.workflows.chat.builder import build_graph
from src.models import GraphState

logging.basicConfig(level=logging.INFO)

async def test_doc_gen_flow():
    graph = build_graph()
    
    print("--- STARTING WORKFLOW ---")
    
    # 1. Initial Query
    state = GraphState(user_query="I need a rent agreement")
    
    print(f"Step 1: User Query -> {state['user_query']}")
    
    # Run until first interrupt (user input request)
    # We use astream to debug or just invoke
    # Since the graph has an interrupt at Document Generation (returning pending_clarification),
    # invoke() should stop and return the state WITH pending_clarification set.
    
    result = await graph.ainvoke(state)
    
    # Check if we got a clarification request
    if result.get("pending_clarification"):
        print("\n--- INTERRUPT RECEIVED ---")
        param = result['pending_clarification']
        print(f"Question: {param['question']}")
        
        # 2. Provide User Input
        print("\n--- PROVIDING USER INPUT ---")
        # Simulating user response
        user_response = "monthly_rent: 5000, security_deposit: 10000, tenant_name: John Doe"
        
        # We need to construct the state to RESUME.
        # Ideally, we append to clarification_history as usage pattern in socket handler
        clarification_history = result.get("clarification_history", [])
        clarification_history.append({
            "question": param['question'],
            "answer": user_response
        })
        
        # Resume state
        # We need to preserve document_generation_state
        resume_state = {
            "user_query": state['user_query'],
            "router_output": result.get("router_output"),
            "orchestrator_plan": result.get("orchestrator_plan"),
            "document_generation_state": result.get("document_generation_state"),
            "clarification_history": clarification_history
        }
        
        # Clear pending clarification
        # NOTE: In the real app, we re-run the loop.
        # But here, we can just call invoke(resume_state). 
        # The document_generation_node checks 'status' == 'waiting_for_input' AND history.
        
        print("Resuming workflow with user input...")
        final_result = await graph.ainvoke(resume_state)
        
        print("\n--- FINAL RESULT ---")
        doc_state = final_result.get("document_generation_state")
        if doc_state:
            print(f"Status: {doc_state['status']}")
            print(f"Generated Document (Preview): {str(doc_state['generated_document'])[:100]}...")
            print(f"Generated Procedure (Preview): {str(doc_state['generated_procedure'])[:100]}...")
        else:
            print("Error: No document state found.")
            
    else:
        print("Flow did not break for user input. Result keys:", result.keys())

if __name__ == "__main__":
    asyncio.run(test_doc_gen_flow())
