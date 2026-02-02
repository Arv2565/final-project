#!/usr/bin/env python3
"""
Enhanced Incremental Ingestion Pipeline with Caching.

This script extends the existing RAG ingestion pipeline with:
- Smart caching to prevent redundant reprocessing
- Support for new document sources (TXT, PDF)
- Automatic pipeline execution
- Consistent metadata tagging and schema

Usage examples:
    # Run incremental ingestion (processes only new files)
    python enhanced_incremental_ingestion.py --directory data/knowledge_base/

    # Force reprocess all files (ignores cache)
    python enhanced_incremental_ingestion.py --directory data/knowledge_base/ --force-reprocess

    # Preview what will be processed
    python enhanced_incremental_ingestion.py --directory data/knowledge_base/ --preview

    # Clear cache and start fresh
    python enhanced_incremental_ingestion.py --clear-cache
"""

import argparse
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the src directory to the path
# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.cache_manager import IngestionCacheManager
from pipelines.legal_document_ingestion import get_ingestion_workflow, cleanup_workflow
from src.config import get_settings, validate_environment

class EnhancedIncrementalIngestion:
    """
    Enhanced ingestion pipeline with caching and multi-format support.
    
    Features:
    - Intelligent caching to avoid reprocessing
    - Support for JSON, TXT, and PDF files
    - Maintains existing RAG architecture
    - Consistent metadata and tagging
    """
    
    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_manager = IngestionCacheManager(cache_file)
        self.workflow = None
        
        # Supported file extensions
        self.supported_extensions = {".json", ".txt", ".pdf"}
    
    def find_processable_files(self, directory: Path, recursive: bool = True) -> List[Path]:
        """
        Find all processable files in the directory.
        
        Args:
            directory: Directory to search
            recursive: Whether to search recursively
            
        Returns:
            List of paths to processable files
        """
        files = []
        
        if recursive:
            for ext in self.supported_extensions:
                files.extend(directory.rglob(f"*{ext}"))
        else:
            for ext in self.supported_extensions:
                files.extend(directory.glob(f"*{ext}"))
        
        return sorted(files)
    
    def preview_processing_plan(self, directory: Path, recursive: bool = True) -> Dict[str, Any]:
        """
        Preview what files will be processed without actually processing them.
        
        Args:
            directory: Directory to search
            recursive: Whether to search recursively
            
        Returns:
            Dictionary with processing plan details
        """
        print("🔍 INCREMENTAL INGESTION PREVIEW")
        print("=" * 60)
        
        # Find all files
        all_files = self.find_processable_files(directory, recursive)
        print(f"📁 Total files found: {len(all_files)}")
        
        # Get cache stats
        cache_stats = self.cache_manager.get_cache_stats()
        print(f"📊 Previously processed files: {cache_stats['total_processed_files']}")
        
        # Filter unprocessed files
        unprocessed_files = self.cache_manager.get_unprocessed_files(all_files)
        
        print(f"🆕 Files to process: {len(unprocessed_files)}\n")
        
        # Group by file type
        file_types = {}
        for file_path in unprocessed_files:
            ext = file_path.suffix.lower()
            if ext not in file_types:
                file_types[ext] = []
            file_types[ext].append(file_path)
        
        # Show details by type
        total_size = 0
        for ext, files in file_types.items():
            print(f"📄 {ext.upper()} files ({len(files)}):") 
            for file_path in files:
                size = file_path.stat().st_size
                total_size += size
                print(f"   • {file_path.name} ({size:,} bytes)")
            print()
        
        # Show cached files
        if cache_stats['recent_files']:
            print("💾 Recently processed files (cached):")
            for filename in cache_stats['recent_files']:
                print(f"   ✓ {filename}")
            print()
        
        print(f"💾 Total size to process: {total_size:,} bytes")
        print(f"⏱️  Cache last updated: {cache_stats.get('last_updated', 'Never')}")
        
        return {
            "total_files_found": len(all_files),
            "cached_files_count": cache_stats['total_processed_files'],
            "files_to_process": len(unprocessed_files),
            "unprocessed_files": unprocessed_files,
            "total_size_to_process": total_size,
            "file_types": {ext: len(files) for ext, files in file_types.items()}
        }
    
    def run_incremental_ingestion(self, directory: Path, recursive: bool = True, 
                                 force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Run the incremental ingestion pipeline.
        
        Args:
            directory: Directory containing documents to process
            recursive: Whether to search recursively
            force_reprocess: If True, ignore cache and reprocess all files
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        print("🚀 ENHANCED INCREMENTAL INGESTION PIPELINE")
        print("=" * 60)
        
        # Find all files
        all_files = self.find_processable_files(directory, recursive)
        print(f"📁 Total files found: {len(all_files)}")
        
        # Determine files to process
        if force_reprocess:
            files_to_process = all_files
            print("🔄 Force reprocess enabled - ignoring cache")
        else:
            files_to_process = self.cache_manager.get_unprocessed_files(all_files)
            print(f"💾 Using cache - {len(files_to_process)} files to process")
        
        if not files_to_process:
            print("✅ No files to process - all files are already cached!")
            return {
                "total_files": len(all_files),
                "processed_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "processing_time": 0.0,
                "skipped_cached": len(all_files)
            }
        
        print(f"\n📋 Files to process:")
        for file_path in files_to_process:
            print(f"   • {file_path.name} ({file_path.suffix})")
        
        # Initialize workflow
        try:
            self.workflow = get_ingestion_workflow()
            print(f"✅ Workflow initialized")
        except Exception as e:
            print(f"❌ Failed to initialize workflow: {e}")
            return {"error": f"Workflow initialization failed: {e}"}
        
        # Process files
        results = {
            "total_files": len(all_files),
            "processed_files": len(files_to_process),
            "successful_files": 0,
            "failed_files": 0,
            "processing_time": 0.0,
            "skipped_cached": len(all_files) - len(files_to_process),
            "file_results": []
        }
        
        print(f"\n📊 PROCESSING RESULTS")
        print("-" * 40)
        
        for file_path in files_to_process:
            print(f"\n📄 Processing: {file_path.name}")
            try:
                # Create enhanced metadata for this file type
                enhanced_metadata = self._create_enhanced_metadata(file_path)
                
                # Process the file
                file_result = self.workflow.ingest_single_document(file_path, enhanced_metadata)
                
                if file_result.success:
                    results["successful_files"] += 1
                    
                    # Mark as processed in cache
                    processing_info = {
                        "chunks_created": file_result.chunks_created,
                        "points_stored": len(file_result.points_stored),
                        "file_type": file_path.suffix.lower()
                    }
                    
                    self.cache_manager.mark_file_processed(file_path, processing_info)
                    
                    print(f"✅ SUCCESS: {file_result.chunks_created} chunks, {len(file_result.points_stored)} points stored")
                    
                    results["file_results"].append({
                        "file": file_path.name,
                        "success": True,
                        "chunks": file_result.chunks_created,
                        "points": len(file_result.points_stored)
                    })
                else:
                    results["failed_files"] += 1
                    print(f"❌ FAILED: {file_result.error}")
                    
                    results["file_results"].append({
                        "file": file_path.name,
                        "success": False,
                        "error": file_result.error
                    })
                    
            except Exception as e:
                results["failed_files"] += 1
                print(f"💥 ERROR: {e}")
                
                results["file_results"].append({
                    "file": file_path.name,
                    "success": False,
                    "error": str(e)
                })
        
        results["processing_time"] = time.time() - start_time
        
        # Final summary
        print(f"\n🎉 INGESTION COMPLETE")
        print("=" * 60)
        print(f"📁 Total files found: {results['total_files']}")
        print(f"💾 Files skipped (cached): {results['skipped_cached']}")
        print(f"🔄 Files processed: {results['processed_files']}")
        print(f"✅ Successful: {results['successful_files']}")
        print(f"❌ Failed: {results['failed_files']}")
        print(f"⏱️  Processing time: {results['processing_time']:.2f} seconds")
        
        if results["successful_files"] > 0:
            total_chunks = sum(r.get("chunks", 0) for r in results["file_results"] if r["success"])
            total_points = sum(r.get("points", 0) for r in results["file_results"] if r["success"])
            print(f"📦 Total chunks created: {total_chunks}")
            print(f"🎯 Total points stored: {total_points}")
            print(f"\n🔍 Ready for search! Query the enhanced legal knowledge base.")
        
        return results
    
    def _create_enhanced_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Create enhanced metadata for different file types."""
        base_metadata = {
            "document_source": "enhanced_legal_collection",
            "processing_method": "incremental_ingestion_v2",
            "ingestion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "file_type": file_path.suffix.lower(),
            "original_filename": file_path.name
        }
        
        # Add file-type specific metadata
        if file_path.suffix.lower() == ".txt":
            base_metadata.update({
                "document_format": "structured_text",
                "processing_strategy": "section_aware_chunking"
            })
        elif file_path.suffix.lower() == ".pdf":
            base_metadata.update({
                "document_format": "portable_document",
                "processing_strategy": "pdf_extraction_with_structure"
            })
        elif file_path.suffix.lower() == ".json":
            base_metadata.update({
                "document_format": "structured_json",
                "processing_strategy": "legal_json_enhanced"
            })
        
        return base_metadata
    
    def clear_cache(self):
        """Clear the processing cache."""
        print("🧹 CLEARING CACHE")
        print("-" * 30)
        
        stats = self.cache_manager.get_cache_stats()
        print(f"📊 Files currently cached: {stats['total_processed_files']}")
        
        self.cache_manager.clear_cache()
        print("✅ Cache cleared successfully")
        print("⚠️  All files will be reprocessed on next run")
    
    def get_cache_stats(self):
        """Display cache statistics."""
        print("📊 CACHE STATISTICS")
        print("-" * 30)
        
        stats = self.cache_manager.get_cache_stats()
        
        print(f"📁 Total processed files: {stats['total_processed_files']}")
        print(f"📍 Cache file location: {stats['cache_file_path']}")
        print(f"💾 Cache file exists: {stats['cache_file_exists']}")
        print(f"⏱️  Last updated: {stats.get('last_updated', 'Never')}")
        
        if stats['recent_files']:
            print(f"\n🕒 Recently processed files:")
            for filename in stats['recent_files']:
                print(f"   • {filename}")
        
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        if self.workflow:
            cleanup_workflow()

def main():
    """Main entry point for enhanced incremental ingestion."""
    parser = argparse.ArgumentParser(
        description="Enhanced Incremental Ingestion Pipeline with Caching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Main action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--directory", "-d", help="Directory containing documents to process")
    action_group.add_argument("--clear-cache", action="store_true", help="Clear the processing cache")
    action_group.add_argument("--cache-stats", action="store_true", help="Show cache statistics")
    
    # Processing options
    parser.add_argument("--preview", "-p", action="store_true", 
                       help="Preview processing plan without actually processing")
    parser.add_argument("--force-reprocess", "-f", action="store_true",
                       help="Force reprocess all files (ignore cache)")
    parser.add_argument("--recursive", "-r", action="store_true", default=True,
                       help="Search directory recursively (default: True)")
    parser.add_argument("--cache-file", help="Custom cache file path")
    
    args = parser.parse_args()
    
    # Validate environment
    print("🔧 Validating environment configuration...")
    if not validate_environment():
        print("❌ Environment validation failed!")
        print("💡 Please check your configuration settings:")
        print("   - QDRANT_HOST and QDRANT_PORT")
        print("   - LEGAL_BERT_MODEL")
        print("   - Other required environment variables")
        return 1
    
    settings = get_settings()
    print(f"✅ Environment validated")
    print(f"🔗 Qdrant: {settings.qdrant.host}:{settings.qdrant.port}")
    print(f"🤖 Model: {settings.embedding.model_name}")
    print(f"📊 Collection: {settings.qdrant.collection_name}")
    print()
    
    # Initialize enhanced ingestion pipeline
    cache_file = Path(args.cache_file) if args.cache_file else None
    pipeline = EnhancedIncrementalIngestion(cache_file)
    
    try:
        # Execute requested action
        if args.clear_cache:
            pipeline.clear_cache()
            
        elif args.cache_stats:
            pipeline.get_cache_stats()
            
        elif args.directory:
            directory_path = Path(args.directory)
            if not directory_path.exists():
                print(f"❌ Directory not found: {directory_path}")
                return 1
            
            if args.preview:
                pipeline.preview_processing_plan(directory_path, args.recursive)
            else:
                results = pipeline.run_incremental_ingestion(
                    directory_path, 
                    args.recursive, 
                    args.force_reprocess
                )
                
                # Return error code if there were failures
                if "error" in results:
                    return 1
                elif results.get("failed_files", 0) > 0:
                    print(f"⚠️  Some files failed to process")
                    return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return 1
    finally:
        pipeline.cleanup()

if __name__ == "__main__":
    sys.exit(main())