#!/usr/bin/env python3
"""
Example script for ingesting legal documents using the streamlined workflow.

This script demonstrates the complete three-step process:
1. Extract and preprocess legal documents (PDF/JSON)
2. Generate embeddings using inLegalBERT
3. Store embeddings with metadata in Qdrant

Usage examples:
    # Ingest a single document
    python ingest_legal_documents.py --file /path/to/document.pdf

    # Ingest all documents from a directory
    python ingest_legal_documents.py --directory /path/to/documents/

    # Ingest with custom metadata
    python ingest_legal_documents.py --file judgment.pdf --court "Supreme Court" --date "2023-01-15"

    # Search for similar documents
    python ingest_legal_documents.py --search "contract breach damages"
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows.legal_document_ingestion import get_ingestion_workflow, cleanup_workflow
from config.settings import get_settings, validate_environment

def create_metadata_from_args(args) -> Optional[Dict[str, Any]]:
    """Create metadata dictionary from command line arguments."""
    metadata = {}
    
    if hasattr(args, 'court') and args.court:
        metadata['court'] = args.court
    if hasattr(args, 'date') and args.date:
        metadata['date'] = args.date
    if hasattr(args, 'case_number') and args.case_number:
        metadata['case_number'] = args.case_number
    if hasattr(args, 'jurisdiction') and args.jurisdiction:
        metadata['jurisdiction'] = args.jurisdiction
    if hasattr(args, 'case_type') and args.case_type:
        metadata['case_type'] = args.case_type
    
    return metadata if metadata else None

def ingest_single_file(file_path: str, metadata: Optional[Dict[str, Any]] = None):
    """Ingest a single legal document."""
    print(f"🚀 Starting ingestion for: {file_path}")
    print("=" * 60)
    
    try:
        workflow = get_ingestion_workflow()
        result = workflow.ingest_single_document(file_path, metadata)
        
        if result.success:
            print(f"✅ Successfully processed {Path(file_path).name}")
            print(f"📄 Chunks created: {result.chunks_created}")
            print(f"🔍 Points stored in Qdrant: {len(result.points_stored)}")
            print(f"🆔 Point IDs: {result.points_stored[:3]}{'...' if len(result.points_stored) > 3 else ''}")

            # Index document into Neo4j to capture hierarchical triples
            try:
                from workflows.graphs.graph_rag_indexer import GraphRAGIndexer
                indexer = GraphRAGIndexer(create_vector_index=False)
                print(f"🔗 Indexing {Path(file_path).name} into Neo4j for hierarchical relations...")
                indexer.index_json_files(paths=[Path(file_path)], recursive=False, max_chunks_per_file=50, embed_entities=False)
                print(f"✅ Graph indexing completed for {Path(file_path).name}")
            except Exception as e:
                print(f"⚠️  Graph indexing failed for {Path(file_path).name}: {e}")
        else:
            print(f"❌ Failed to process {Path(file_path).name}")
            print(f"🚫 Error: {result.error}")
            
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
    finally:
        cleanup_workflow()

def ingest_directory(directory_path: str, recursive: bool = True, file_pattern: str = "*"):
    """Ingest all legal documents from a directory."""
    print(f"🚀 Starting batch ingestion from: {directory_path}")
    print(f"🔄 Recursive: {recursive}, Pattern: {file_pattern}")
    print("=" * 60)
    
    try:
        workflow = get_ingestion_workflow()
        result = workflow.ingest_directory(
            directory_path=directory_path,
            recursive=recursive,
            file_pattern=file_pattern
        )
        
        print("\n📊 INGESTION RESULTS")
        print("=" * 60)
        print(f"📁 Total files processed: {result.total_files}")
        print(f"✅ Successful: {result.successful_files}")
        print(f"❌ Failed: {result.failed_files}")
        print(f"📄 Total chunks: {result.total_chunks}")
        print(f"🔍 Points stored: {len(result.stored_points)}")
        print(f"⏱️  Processing time: {result.processing_time:.2f} seconds")
        
        if result.errors:
            print(f"\n🚫 ERRORS ({len(result.errors)}):")
            for error in result.errors:
                print(f"   • {error['file']}: {error['error']}")
                
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
    finally:
        cleanup_workflow()

def search_documents(query_text: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None):
    """Search for similar legal documents."""
    print(f"🔍 Searching for: '{query_text}'")
    print(f"📊 Limit: {limit}")
    if filters:
        print(f"🔧 Filters: {filters}")
    print("=" * 60)
    
    try:
        workflow = get_ingestion_workflow()
        results = workflow.search_similar_documents(
            query_text=query_text,
            limit=limit,
            filters=filters
        )
        
        if results:
            print(f"📋 Found {len(results)} similar documents:")
            print("=" * 60)
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Score: {result['score']:.4f}")
                print(f"   📄 Source: {result['metadata'].get('source_file', 'Unknown')}")
                print(f"   🏛️  Court: {result['metadata'].get('court', 'Unknown')}")
                print(f"   📅 Date: {result['metadata'].get('date', 'Unknown')}")
                print(f"   📝 Text: {result['text'][:200]}...")
        else:
            print("📭 No similar documents found.")
            
    except Exception as e:
        print(f"💥 Search error: {e}")
    finally:
        cleanup_workflow()

def check_collection_status():
    """Check the status of the Qdrant collection."""
    print("🔍 Checking Qdrant collection status...")
    print("=" * 60)
    
    try:
        workflow = get_ingestion_workflow()
        status = workflow.get_collection_status()
        
        print(json.dumps(status, indent=2))
        
    except Exception as e:
        print(f"💥 Status check error: {e}")
    finally:
        cleanup_workflow()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Legal Document Ingestion Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Main action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--file", "-f", help="Ingest a single document file")
    action_group.add_argument("--directory", "-d", help="Ingest all documents from a directory")
    action_group.add_argument("--search", "-s", help="Search for similar documents")
    action_group.add_argument("--status", action="store_true", help="Check collection status")
    
    # Directory options
    parser.add_argument("--recursive", "-r", action="store_true", default=True,
                       help="Search directory recursively (default: True)")
    parser.add_argument("--pattern", "-p", default="*",
                       help="File pattern to match (default: *)")
    
    # Metadata options
    parser.add_argument("--court", help="Court name metadata")
    parser.add_argument("--date", help="Date metadata (YYYY-MM-DD)")
    parser.add_argument("--case-number", help="Case number metadata")
    parser.add_argument("--jurisdiction", help="Jurisdiction metadata")
    parser.add_argument("--case-type", help="Case type metadata")
    
    # Search options
    parser.add_argument("--limit", "-l", type=int, default=10,
                       help="Maximum number of search results (default: 10)")
    parser.add_argument("--filter-court", help="Filter search by court")
    parser.add_argument("--filter-jurisdiction", help="Filter search by jurisdiction")
    
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
    
    # Execute the requested action
    if args.file:
        metadata = create_metadata_from_args(args)
        ingest_single_file(args.file, metadata)
        
    elif args.directory:
        ingest_directory(args.directory, args.recursive, args.pattern)
        
    elif args.search:
        # Prepare search filters
        filters = {}
        if args.filter_court:
            filters['court'] = args.filter_court
        if args.filter_jurisdiction:
            filters['jurisdiction'] = args.filter_jurisdiction
        
        search_documents(args.search, args.limit, filters if filters else None)
        
    elif args.status:
        check_collection_status()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())