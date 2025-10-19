#!/usr/bin/env python3
"""
Script to extract legal knowledge from PDF documents in the central acts folder.

This script uses LangChain to process legal documents and extract structured
knowledge including title, purpose, scope, key provisions, and administration.
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from agents.legal_knowledge_extractor import LegalDocumentKnowledgeExtractor


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"legal_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )


def find_central_acts_directory() -> Path:
    """Find the central acts directory in the project."""
    project_root = Path(__file__).parent.parent
    
    # Try different possible locations
    possible_locations = [
        project_root / "data" / "raw" / "central_acts",
        project_root / "data" / "knowledge_base" / "central_acts",
        project_root / "data" / "central_acts"
    ]
    
    for location in possible_locations:
        if location.exists():
            return location
    
    # If no central acts directory found, check the entire data directory
    data_dir = project_root / "data"
    if data_dir.exists():
        return data_dir
    
    raise FileNotFoundError("Could not find central acts directory or data directory")


def main():
    """Main function to run legal knowledge extraction."""
    parser = argparse.ArgumentParser(
        description="Extract legal knowledge from PDF documents using LangChain"
    )
    parser.add_argument(
        "--directory",
        type=str,
        help="Directory containing PDF files (default: auto-detect central acts folder)"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Single PDF file to process"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="legal_knowledge_extraction.json",
        help="Output JSON file name (default: legal_knowledge_extraction.json)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Search subdirectories recursively (default: True)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Check for OpenAI API key
        if not os.getenv('OPENAI_API_KEY'):
            logger.error("OPENAI_API_KEY environment variable not set")
            logger.error("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
            sys.exit(1)
        
        # Initialize extractor
        logger.info("Initializing Legal Document Knowledge Extractor...")
        extractor = LegalDocumentKnowledgeExtractor()
        
        results = []
        
        if args.file:
            # Process single file
            pdf_path = Path(args.file)
            if not pdf_path.exists():
                logger.error(f"File not found: {pdf_path}")
                sys.exit(1)
            
            logger.info(f"Processing single file: {pdf_path}")
            knowledge = extractor.extract_from_pdf(pdf_path)
            if knowledge:
                results.append((pdf_path, knowledge))
                logger.info(f"✅ Successfully processed: {pdf_path.name}")
            else:
                logger.error(f"❌ Failed to process: {pdf_path.name}")
                
        elif args.directory:
            # Process directory
            directory_path = Path(args.directory)
            if not directory_path.exists():
                logger.error(f"Directory not found: {directory_path}")
                sys.exit(1)
            
            logger.info(f"Processing directory: {directory_path}")
            results = extractor.extract_from_directory(directory_path, args.recursive)
            
        else:
            # Auto-detect central acts directory
            try:
                central_acts_dir = find_central_acts_directory()
                logger.info(f"Auto-detected directory: {central_acts_dir}")
                results = extractor.extract_from_directory(central_acts_dir, args.recursive)
            except FileNotFoundError as e:
                logger.error(f"Could not find central acts directory: {e}")
                sys.exit(1)
        
        # Save results
        if results:
            output_path = Path(args.output)
            extractor.save_results_to_json(results, output_path)
            
            logger.info(f"\n=== EXTRACTION COMPLETE ===")
            logger.info(f"Processed {len(results)} PDF files")
            logger.info(f"Results saved to: {output_path}")
            
            # Print summary
            print(f"\n📋 Legal Knowledge Extraction Summary")
            print(f"{'='*50}")
            print(f"📁 Documents processed: {len(results)}")
            print(f"💾 Output file: {output_path}")
            print(f"✅ Extraction complete!")
            
            # Preview first result
            if results:
                first_file, first_knowledge = results[0]
                print(f"\n📄 Preview - {first_file.name}:")
                print(f"   Title: {first_knowledge.title[:100]}...")
                print(f"   Purpose: {first_knowledge.purpose[:100]}...")
                print(f"   Key provisions: {len(first_knowledge.key_provisions)} items")
        else:
            logger.warning("No PDF files were successfully processed")
            print("⚠️  No PDF files found or processed successfully")
    
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()