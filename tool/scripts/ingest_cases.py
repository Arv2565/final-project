#!/usr/bin/env python3
"""
CLI Script for Case Data Ingestion.

Usage:
    python ingest_cases.py --source tool/data/casefiles.json
    python ingest_cases.py --source tool/data/casefiles.json --refresh
    python ingest_cases.py --source tool/data/casefiles.json --sample 10
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tool.pipelines.document_ingestion.case_ingester import CaseIngestionPipeline


def setup_logging(level=logging.INFO):
    """Configure logging for the CLI."""
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    
    return root_logger


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest case data from casefiles.json into Qdrant and Neo4j databases"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        default="tool/data/casefiles.json",
        help="Path to casefiles.json (default: tool/data/casefiles.json)"
    )
    
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Clear existing collections before ingestion (destructive)"
    )
    
    parser.add_argument(
        "--sample",
        type=int,
        help="Limit ingestion to first N cases for testing"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(log_level)
    
    logger.info("Case Ingestion Pipeline Started")
    logger.info(f"Source file: {args.source}")
    
    # Validate file exists
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error(f"Source file not found: {args.source}")
        sys.exit(1)
    
    if not source_path.is_file():
        logger.error(f"Source is not a file: {args.source}")
        sys.exit(1)
    
    logger.info(f"Source file verified: {source_path.stat().st_size} bytes")
    
    if args.refresh:
        logger.warning("⚠️  REFRESH FLAG SET - Existing collections will be cleared!")
    
    if args.sample:
        logger.info(f"Sample mode: Processing first {args.sample} cases only")
    
    try:
        # Run ingestion pipeline
        pipeline = CaseIngestionPipeline()
        
        stats = pipeline.ingest_from_file(
            filepath=str(source_path),
            refresh=args.refresh
        )
        
        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("INGESTION COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info(f"✓ Cases processed:        {stats['cases_processed']}")
        logger.info(f"✓ Total chunks created:   {stats['chunks_created']}")
        logger.info(f"✓ Embeddings generated:   {stats['embeddings_generated']}")
        logger.info(f"✓ Qdrant chunks stored:   {stats['qdrant_stored']}")
        logger.info(f"✓ Neo4j nodes created:    {stats['neo4j_nodes_created']}")
        logger.info(f"✓ Neo4j relations:        {stats['neo4j_relations_created']}")
        if stats['errors'] > 0:
            logger.warning(f"⚠ Errors encountered:      {stats['errors']}")
        logger.info("=" * 70)
        
        # Cleanup
        pipeline.cleanup()
        
        logger.info("Pipeline completed successfully!")
        sys.exit(0)
    
    except KeyboardInterrupt:
        logger.info("\nIngestion interrupted by user")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Ingestion failed with error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
