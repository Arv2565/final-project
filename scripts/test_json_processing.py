#!/usr/bin/env python3
"""
Simple test script to verify JSON processing without dependencies.
This tests the enhanced document processing logic.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def simple_test_json_processing():
    """Test the JSON processing without requiring full dependencies."""
    
    print("🧪 Testing Enhanced JSON Processing Logic")
    print("=" * 50)
    
    # Import just the document processor
    try:
        from processing.document_processor import DocumentProcessor
        print("✅ Successfully imported DocumentProcessor")
    except Exception as e:
        print(f"❌ Failed to import: {e}")
        return
    
    # Find JSON files
    data_dir = Path(__file__).parent.parent / "data" / "knowledge_base"
    json_files = list(data_dir.glob("*.json"))
    
    print(f"\n📁 Found {len(json_files)} JSON files:")
    for file_path in json_files:
        print(f"   • {file_path.name}")
    
    if not json_files:
        print("❌ No JSON files found in data directory")
        return
    
    # Test processing a few files
    processor = DocumentProcessor()
    
    for i, file_path in enumerate(json_files[:3]):  # Test first 3 files
        print(f"\n📄 Testing: {file_path.name}")
        print("-" * 40)
        
        try:
            # Process the document
            chunks = processor.process_document(file_path)
            
            print(f"✅ Successfully processed {file_path.name}")
            print(f"   📦 Chunks created: {len(chunks)}")
            
            if chunks:
                # Show first chunk details
                first_chunk = chunks[0]
                print(f"   📝 First chunk preview:")
                print(f"      • Text length: {len(first_chunk.text)}")
                print(f"      • Metadata keys: {list(first_chunk.metadata.keys())}")
                print(f"      • Source: {first_chunk.metadata.get('source', 'Unknown')}")
                print(f"      • Category: {first_chunk.metadata.get('category', 'Unknown')}")
                
                # Show sample text (first 200 chars)
                sample_text = first_chunk.text[:200].replace('\n', ' ')
                print(f"      • Sample: {sample_text}...")
                
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
    
    print("\n🎉 JSON Processing Test Complete!")

if __name__ == "__main__":
    simple_test_json_processing()