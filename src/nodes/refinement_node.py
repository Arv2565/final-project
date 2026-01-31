
import re
from typing import Dict, Any, List
from src.models import GraphState

def refinement_node(state: GraphState) -> Dict[str, Any]:
    """
    Node to analyze the generated document content for missing details (placeholders).
    If placeholders are found, it lists them for the user in the final response 
    while preserving the raw draft for PDF generation.
    """
    print("\n🔍 REFINEMENT NODE")
    print("=" * 60)
    
    final_response = state.get("final_response", "")
    
    # Check for various placeholder patterns
    # 1. [MISSING: Description]
    # 2. [BLANK]
    # 3. [PLACE], [DATE], [YEAR]
    # 4. [Generic Capitalized Placeholders like SIGNATURE]
    
    # Combined regex:
    # \[MISSING:\s*(.*?)\]  -> Matches [MISSING: ...]
    # |                     -> OR
    # \[(?!.*\[)(.*?)\]     -> Matches [...] but excludes [ x ] checkboxes if any, and avoids nested brackets
    # Actually, simpler approach for this specific output style:
    
    # Capture anything in square brackets that looks like a placeholder
    # We filter out common non-placeholders if needed (like [1], [a]) later if they appear
    
    # Pattern 1: Explicit MISSING
    missing_explicit = re.findall(r'\[MISSING:\s*(.*?)\]', final_response)
    
    # Pattern 2: Generic Uppercase/Titlecase placeholders e.g. [Place], [Date], [Signature]
    # We avoid [1], [a], [x] by requiring at least 2 letters
    missing_generic = re.findall(r'\[([A-Z][a-zA-Z\s/_]+)\]', final_response)
    
    # Filter out "MISSING" from generic to avoid duplicates if the model output [MISSING: ...] which matches generic too
    missing_generic = [item for item in missing_generic if not item.startswith("MISSING:")]
    
    # specific fix for [BLANK] -> treat as "Details"
    missing_generic = ["Details" if item == "BLANK" else item for item in missing_generic]

    missing_items = missing_explicit + missing_generic
    
    updates = {}
    
    # Always save the raw draft content for the PDF generator
    updates["generated_document_content"] = final_response
    
    if missing_items:
        print(f"⚠️  Found {len(missing_items)} missing details in difference.")
        unique_items = sorted(list(set(missing_items)))
        
        # 1. Generate Draft DOCX immediately
        import time
        from src.utils.docx_generator import generate_docx_report
        timestamp = int(time.time())
        draft_filename = f"output/draft_{timestamp}.docx"
        print(f"\n📄 Generating DRAFT Document with placeholders: {draft_filename}")
        
        # Construct the "REQUIRED INFORMATION" section
        start_marker = "=" * 40
        header = "REQUIRED INFORMATION TO FINALIZE DRAFT"
        end_marker = "=" * 40
        
        missing_info_section = f"\n\n{start_marker}\n\n{header}\n\n{end_marker}\n\n"
        missing_info_section += "The generated document contains missing details. Please provide the following to complete the draft:\n\n"
        
        for i, item in enumerate(unique_items, 1):
             missing_info_section += f"{i}. {item}\n\n"
             
        missing_info_section += "Once provided, I can generate the final execution version."
        
        # Create draft content by appending the list (but keeping placeholders in main text)
        draft_content = final_response + missing_info_section
        
        print(f"\n📄 Generating DRAFT Document with placeholders: {draft_filename}")
        generate_docx_report(draft_content, draft_filename)
        print(f"✅ Draft generated. Identifying missing details...")
        
        # 2. Interactive Input Loop
        print("\n" + "="*60)
        print("📝 INTERACTIVE DOCUMENT COMPLETION")
        print("The generated draft requires specific details.")
        print("Please enter the values below to finalize the document.")
        print("="*60 + "\n")
        
        filled_text = final_response
        for item in unique_items:
            # Prompt user
            user_value = input(f"Enter value for '{item}': ").strip()
            
            # Use a default if empty? Strictness suggests we need a value.
            if not user_value:
                user_value = "[BLANK]" 
            
            # Replace ALL occurrences of [MISSING: item] with BOLDED value
            # Markdown bold syntax: **value**
            replacement = f"**{user_value}**"
            
            # Replace occurrences. We need to handle:
            # 1. [MISSING: item]
            # 2. [item] (if item came from generic regex)
            # 3. [BLANK] if item was "Details" (mapped from BLANK)
            
            replacement = f"**{user_value}**"
            
            # Try replacing [MISSING: item]
            pattern_missing = re.escape(f"[MISSING: {item}]")
            filled_text = re.sub(pattern_missing, replacement, filled_text)
            
            # Try replacing [item]
            pattern_generic = re.escape(f"[{item}]")
            filled_text = re.sub(pattern_generic, replacement, filled_text)
            
            # Try replacing [BLANK] if item is "Details"
            if item == "Details":
                 filled_text = re.sub(re.escape("[BLANK]"), replacement, filled_text)
            
        print("\n✅ All details collected. Generating Final Document...")
        
        # Update specific fields
        # 'generated_document_content' gets the FILLED text -> Final PDF will use this
        updates["generated_document_content"] = filled_text
        
        # 'final_response' gets the filled text so Chat output matches
        updates["final_response"] = filled_text
        
    else:
        print("✅ No missing details found.")
        
    return updates
