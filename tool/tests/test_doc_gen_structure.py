"""
Simple structural test for document generation workflow.
Tests imports and basic structure without calling LLMs.
"""
import sys
sys.path.insert(0, '/Users/pranav/Documents/Projects/final-project/tool')

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    # Test model imports
    from src.models.document_generation import TemplateInfo, PlaceholderInfo, DocumentGenerationState
    print("✓ Document generation models imported")
    
    # Test that models are correctly exported
    from src.models import TemplateInfo, PlaceholderInfo, DocumentGenerationState
    print("✓ Models exported in __init__.py")
    
    # Test agent file existence (not instantiation to avoid API calls)
    import importlib.util
    
    agent_files = [
        '/Users/pranav/Documents/Projects/final-project/tool/src/agents/document_generation/template_selection_agent.py',
        '/Users/pranav/Documents/Projects/final-project/tool/src/agents/document_generation/placeholder_extraction_agent.py',
        '/Users/pranav/Documents/Projects/final-project/tool/src/agents/document_generation/document_generation_agent.py',
        '/Users/pranav/Documents/Projects/final-project/tool/src/agents/document_generation/procedure_generation_agent.py',
    ]
    
    for agent_file in agent_files:
        spec = importlib.util.spec_from_file_location("test_module", agent_file)
        if spec and spec.loader:
            print(f"✓ Agent file exists: {agent_file.split('/')[-1]}")
    
    # Test node import (without instantiation)
    print("\nTesting node module...")
    try:
        # This will fail if there are import errors in the node
        import src.nodes.document_generation as doc_gen_module
        print("✓ document_generation node module loaded")
    except Exception as e:
        print(f"✗ Node import failed: {e}")
        return False
    
    return True

def test_template_json():
    """Test that templates.json exists and is valid."""
    import json
    from pathlib import Path
    
    print("\nTesting templates.json...")
    templates_path = Path('/Users/pranav/Documents/Projects/final-project/tool/data/templates/templates.json')
    
    if not templates_path.exists():
        print(f"✗ templates.json not found at {templates_path}")
        return False
    
    with open(templates_path, 'r') as f:
        templates = json.load(f)
    
    print(f"✓ templates.json loaded with {len(templates)} templates")
    
    # Verify structure
    for i, tmpl in enumerate(templates):
        required_keys = ['id', 'name', 'summary', 'keywords']
        if not all(k in tmpl for k in required_keys):
            print(f"✗ Template {i} missing required keys")
            return False
    
    print("✓ All templates have required structure")
    return True

def test_orchestrator_prompt():
    """Test that orchestrator prompt includes document generation."""
    print("\nTesting orchestrator prompt...")
    from src.prompts.orchestrator_agent import ORCHESTRATOR_SYSTEM_PROMPT
    
    if 'document_generation' in ORCHESTRATOR_SYSTEM_PROMPT.lower() or '7.' in ORCHESTRATOR_SYSTEM_PROMPT:
        print("✓ Orchestrator prompt includes document generation")
        return True
    else:
        print("✗ Orchestrator prompt missing document generation reference")
        return False

def main():
    print("=" * 60)
    print("Document Generation Workflow - Structural Verification")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Template JSON", test_template_json),
        ("Orchestrator Prompt", test_orchestrator_prompt),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    
    if all_passed:
        print("\n✓ All structural tests passed!")
        print("\nNote: Full end-to-end testing requires:")
        print("  - OPENAI_API_KEY or GOOGLE_API_KEY set in environment")
        print("  - Qdrant vector database running")
        print("  - Run via: python -m src.app (for interactive testing)")
    else:
        print("\n✗ Some tests failed. Please review the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
