
from src.nodes.refinement_node import refinement_node

# Mock State with a draft containing placeholders
mock_state = {
    "final_response": """DRAFT OF AGREEMENT

This agreement is made on [MISSING: Date] between [MISSING: Landlord Name] and [MISSING: Tenant Name].

WHEREAS the Landlord agrees to lease property at [MISSING: Property Address].
"""
}

print("--- Testing Interactive Refinement Node ---")
print("(This test will PAUSE and ask for terminal input)")
updates = refinement_node(mock_state)

print("\n--- Result ---")
print("Generated Document Content (Final Source for PDF):\n", updates["generated_document_content"])

# Verify replacements
if "[MISSING:" not in updates["generated_document_content"]:
    print("✅ All placeholders replaced!")
else:
    print("❌ Placeholders still present!")
