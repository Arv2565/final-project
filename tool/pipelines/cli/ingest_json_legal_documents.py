#!/usr/bin/env python3
"""
Enhanced JSON Legal Documents Ingestion Script.

This script specifically handles the ingestion of JSON legal documents
with improved categorization and metadata tagging while maintaining
compatibility with the existing RAG structure.

Usage examples:
    # Ingest all JSON files from data directory
    python ingest_json_legal_documents.py --directory data/knowledge_base/

    # Ingest specific JSON file with enhanced metadata
    python ingest_json_legal_documents.py --file data/knowledge_base/crpc.json

    # Preview processing without actually ingesting
    python ingest_json_legal_documents.py --directory data/knowledge_base/ --preview
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

# Add the src directory to the path
# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipelines.legal_document_ingestion import get_ingestion_workflow, cleanup_workflow
from src.config import get_settings, validate_environment

def preview_json_processing(file_path: Path) -> Dict[str, Any]:
    """Preview how a JSON file would be processed without actually ingesting it."""
    print(f"\n📄 Preview processing for: {file_path.name}")
    print("=" * 60)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Basic file info
        print(f"📊 File size: {file_path.stat().st_size:,} bytes")
        print(f"🏗️  Data structure: {'Array' if isinstance(data, list) else 'Object'}")
        
        if isinstance(data, list):
            print(f"📋 Number of items: {len(data)}")
            if data:
                # Sample first item
                first_item = data[0]
                print(f"📝 Sample item keys: {list(first_item.keys())}")
                
                # Check for different JSON structures
                if "section_desc" in first_item:
                    print("🏛️  Structure type: Criminal/Civil Procedure (section_desc)")
                elif "description" in first_item:
                    print("🏛️  Structure type: Motor Vehicle Act (description)")
                elif "chapter,section,section_title,section_desc" in first_item:
                    print("🏛️  Structure type: Hindu Marriage Act (combined fields)")
                else:
                    print("🏛️  Structure type: Unknown/Custom")
        
        # Infer category from filename
        filename_stem = file_path.stem.lower()
        category_map = {
            "crpc": "Criminal Procedure Code",
            "cpc": "Civil Procedure Code",
            "mva": "Motor Vehicle Act", 
            "hma": "Hindu Marriage Act",
            "ida": "Indian Divorce Act",
            "iea": "Indian Evidence Act",
            "nia": "Negotiable Instruments Act"
        }
        
        inferred_category = category_map.get(filename_stem, "Unknown Legal Document")
        print(f"🏷️  Inferred category: {inferred_category}")
        
        # Estimate chunks
        if isinstance(data, list):
            estimated_chunks = len(data)  # Roughly one chunk per section
        else:
            estimated_chunks = 1
        
        print(f"📦 Estimated chunks: ~{estimated_chunks}")
        
        return {
            "file_size": file_path.stat().st_size,
            "structure_type": "array" if isinstance(data, list) else "object",
            "item_count": len(data) if isinstance(data, list) else 1,
            "inferred_category": inferred_category,
            "estimated_chunks": estimated_chunks
        }
        
    except Exception as e:
        print(f"❌ Error previewing {file_path.name}: {e}")
        return {"error": str(e)}

def ingest_json_files_enhanced(file_paths: List[Path], preview_only: bool = False):
    """Ingest JSON legal documents with enhanced processing."""
    print(f"🚀 Enhanced JSON Legal Documents Ingestion")
    print(f"📁 Processing {len(file_paths)} files")
    print("=" * 60)
    
    if preview_only:
        print("👁️  PREVIEW MODE - No actual ingestion will occur")
        print("=" * 60)
        
        preview_results = {}
        for file_path in file_paths:
            preview_results[file_path.name] = preview_json_processing(file_path)
        
        # Summary
        print("\n📊 PREVIEW SUMMARY")
        print("=" * 60)
        total_size = sum(r.get("file_size", 0) for r in preview_results.values() if "error" not in r)
        total_chunks = sum(r.get("estimated_chunks", 0) for r in preview_results.values() if "error" not in r)
        
        print(f"📁 Total files: {len(file_paths)}")
        print(f"💾 Total size: {total_size:,} bytes")
        print(f"📦 Estimated total chunks: ~{total_chunks}")
        
        categories = {}
        for result in preview_results.values():
            if "error" not in result:
                cat = result.get("inferred_category", "Unknown")
                categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\n🏷️  Categories found:")
        for cat, count in categories.items():
            print(f"   • {cat}: {count} file(s)")
        
        return
    
    # Actual ingestion
    start_time = time.time()
    
    try:
        workflow = get_ingestion_workflow()
        
        # Process each file individually to track progress and handle errors gracefully
        successful_files = 0
        failed_files = 0
        total_chunks = 0
        
        for file_path in file_paths:
            print(f"\n📄 Processing: {file_path.name}")
            print("-" * 40)
            
            try:
                # Create enhanced metadata for JSON legal documents
                enhanced_metadata = {
                    "document_source": "legal_json_collection",
                    "processing_method": "enhanced_json_legal",
                    "ingestion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                result = workflow.ingest_single_document(file_path, enhanced_metadata)
                
                if result.success:
                    successful_files += 1
                    total_chunks += result.chunks_created
                    print(f"✅ Successfully processed {file_path.name}")
                    print(f"   📦 Chunks created: {result.chunks_created}")
                    print(f"   🆔 Points stored: {len(result.points_stored)}")

                    # Additionally, index structural triples into Neo4j for hierarchy
                    try:
                        from pipelines.graphs.graph_rag_indexer import GraphRAGIndexer
                        indexer = GraphRAGIndexer(create_vector_index=False)
                        print(f"🔗 Indexing {file_path.name} into Neo4j for hierarchical relations...")
                        indexer.index_json_files(paths=[file_path], recursive=False, max_chunks_per_file=50, embed_entities=False)
                        print(f"✅ Graph indexing completed for {file_path.name}")
                    except Exception as e:
                        print(f"⚠️  Graph indexing failed for {file_path.name}: {e}")
                else:
                    failed_files += 1
                    print(f"❌ Failed to process {file_path.name}")
                    print(f"   🚫 Error: {result.error}")
                    
            except Exception as e:
                failed_files += 1
                print(f"💥 Unexpected error processing {file_path.name}: {e}")
        
        processing_time = time.time() - start_time
        
        # Final results
        print("\n🎉 INGESTION COMPLETED")
        print("=" * 60)
        print(f"📁 Total files processed: {len(file_paths)}")
        print(f"✅ Successful: {successful_files}")
        print(f"❌ Failed: {failed_files}")
        print(f"📦 Total chunks created: {total_chunks}")
        print(f"⏱️  Processing time: {processing_time:.2f} seconds")
        
        if successful_files > 0:
            print(f"\n🔍 Ready for search! Use the search functionality to query the new legal documents.")
            
    except Exception as e:
        print(f"💥 Critical error during ingestion: {e}")
    finally:
        cleanup_workflow()

def main():
    """Main entry point for the enhanced JSON legal documents ingestion script."""
    parser = argparse.ArgumentParser(
        description="Enhanced JSON Legal Documents Ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Main action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--file", "-f", help="Ingest a single JSON file")
    action_group.add_argument("--directory", "-d", help="Ingest all JSON files from a directory")
    
    # Options
    parser.add_argument("--preview", "-p", action="store_true", 
                       help="Preview processing without actually ingesting")
    parser.add_argument("--recursive", "-r", action="store_true", default=True,
                       help="Search directory recursively (default: True)")
    
    args = parser.parse_args()
    
    # Validate environment
    print("🔧 Validating environment configuration...")
    if not validate_environment():
        print("❌ Environment validation failed!")
        print("💡 Please check your configuration settings:")
        print("   - QDRANT_HOST and QDRANT_PORT")
        print("   - LEGAL_BERT_MODEL (if customized)")
        print("   - Other required environment variables")
        return 1
    
    settings = get_settings()
    print(f"✅ Environment validated")
    print(f"🔗 Qdrant: {settings.qdrant.host}:{settings.qdrant.port}")
    print(f"🤖 Model: {settings.embedding.model_name}")
    print(f"📊 Collection: {settings.qdrant.collection_name}")
    print()
    
    # Collect JSON files to process
    json_files = []
    
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return 1
        if file_path.suffix.lower() != ".json":
            print(f"❌ File is not a JSON file: {file_path}")
            return 1
        json_files = [file_path]
        
    elif args.directory:
        directory_path = Path(args.directory)
        if not directory_path.exists():
            print(f"❌ Directory not found: {directory_path}")
            return 1
        
        if args.recursive:
            json_files = list(directory_path.rglob("*.json"))
        else:
            json_files = list(directory_path.glob("*.json"))
        
        if not json_files:
            print(f"❌ No JSON files found in: {directory_path}")
            return 1
    
    print(f"📁 Found {len(json_files)} JSON file(s) to process:")
    for file_path in json_files:
        print(f"   • {file_path.name}")
    print()
    
    # Process the files
    ingest_json_files_enhanced(json_files, args.preview)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())