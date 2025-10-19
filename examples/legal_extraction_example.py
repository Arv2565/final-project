#!/usr/bin/env python3
"""
Example usage of the Legal Document Knowledge Extractor.

This example shows how to use the LangChain agent to extract structured
knowledge from legal PDF documents.
"""
import os
import sys
from pathlib import Path

# Add project src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from agents.legal_knowledge_extractor import LegalDocumentKnowledgeExtractor


def main():
    """Example usage of the legal knowledge extractor."""
    
    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-key-here'")
        return
    
    print("📄 Legal Document Knowledge Extractor Example")
    print("=" * 50)
    
    # Initialize the extractor
    print("🔧 Initializing extractor...")
    try:
        extractor = LegalDocumentKnowledgeExtractor()
        print("✅ Extractor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize extractor: {e}")
        return
    
    # Find a sample PDF file
    data_dir = project_root / "data"
    sample_pdfs = list(data_dir.rglob("*.pdf"))
    
    if not sample_pdfs:
        print("⚠️  No PDF files found in data directory")
        print("Please add some PDF files to test with")
        return
    
    # Process the first PDF found
    sample_pdf = sample_pdfs[0]
    print(f"\n📖 Processing sample file: {sample_pdf.name}")
    
    try:
        # Extract knowledge
        knowledge = extractor.extract_from_pdf(sample_pdf)
        
        if knowledge:
            print("✅ Extraction successful!")
            print("\n📋 Extracted Knowledge:")
            print("-" * 30)
            
            print(f"📰 Title: {knowledge.title}")
            print(f"🎯 Purpose: {knowledge.purpose[:100]}...")
            print(f"🔍 Scope: {knowledge.scope[:100]}...")
            print(f"📜 Key Provisions ({len(knowledge.key_provisions)} items):")
            for i, provision in enumerate(knowledge.key_provisions, 1):
                print(f"   {i}. {provision[:80]}...")
            print(f"🏛️  Administration: {knowledge.administration[:100]}...")
            
            # Save to JSON
            output_file = project_root / "example_extraction.json"
            extractor.save_results_to_json([(sample_pdf, knowledge)], output_file)
            print(f"\n💾 Results saved to: {output_file}")
            
        else:
            print("❌ Extraction failed")
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")


if __name__ == "__main__":
    main()