import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.workflows.document_generation import DocumentGenerationWorkflow
from src.models.activity_law import ActivityLawState

def main():
    print("Running Document Generation Verification...")
    
    workflow = DocumentGenerationWorkflow()
    
    # Mock User Inputs
    user_inputs = {
        "COURT_NAME": "High Court of Delhi",
        "DISTRICT": "New Delhi",
        "APPLICANT_NAME": "John Doe",
        "FATHER_NAME": "Richard Doe",
        "AGE": "35",
        "RESIDENCE": "123, Baker Street, New Delhi",
        "FIR_NUMBER": "123/2023",
        "POLICE_STATION": "Connaught Place",
        "OFFENCES": "Section 420 IPC",
        "DATE_OF_ARREST": "2023-10-01",
        "GROUNDS_FOR_BAIL": "1. The applicant is innocent.\n2. No recovery is to be effected.",
        "PRAYER": "Grant bail to the applicant."
    }
    
    try:
        # Check if template file exists
        # In this environment, we might not have the actual .docx file if it wasn't there
        # but the list_dir showed bail_application.docx in data/temapalates/
        
        output = workflow.run(state=None, template_id="bail_application", user_inputs=user_inputs)
        print(f"Success! Document generated at: {output}")
        
    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
