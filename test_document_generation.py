
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

from src.workflows.chat.builder import build_graph

def test_document_generation():
    """Run the chat workflow and check if a PDF is generated."""
    
    # 1. Clear output directory (optional, or just count files)
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    initial_files = set(os.listdir(output_dir))
    
    # 2. Build graph
    app = build_graph()
    
    # 3. Invoke with a procedural query
    input_state = {
        "user_query": "What are the procedures for divorce under Hindu Marriage Act?"
    }
    
    print("Invoking graph...")
    result = app.invoke(input_state)
    
    # 4. Check result
    print("\nGraph execution completed.")
    
    final_response = result.get("final_response")
    generated_path = result.get("generated_document_path")
    
    print(f"Final Response present: {bool(final_response)}")
    print(f"Generated Document Path: {generated_path}")
    
    if generated_path and os.path.exists(generated_path):
        print("✅ SUCCESS: PDF file exists.")
    else:
        print("❌ FAILURE: PDF file not found or path missing in state.")
        
        # Check if any new file was created in output/
        current_files = set(os.listdir(output_dir))
        new_files = current_files - initial_files
        if new_files:
             print(f"However, new files were found in output/: {new_files}")

if __name__ == "__main__":
    test_document_generation()
