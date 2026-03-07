#!/usr/bin/env python3
"""Run case ingestion pipeline for casefiles.json."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

from pipelines.document_ingestion.case_ingester import CaseIngestionPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run case ingestion into Qdrant + Neo4j")
    parser.add_argument(
        "-f",
        "--file",
        default="data/casefiles.json",
        help="Path to input case JSON file (default: data/casefiles.json)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Clear existing Qdrant case collection before ingesting",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.file)

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return 1

    print("🚀 Starting case ingestion")
    print(f"📁 Input: {input_path}")
    print(f"♻️ Refresh: {args.refresh}")

    pipeline = CaseIngestionPipeline()
    stats = pipeline.ingest_from_file(filepath=str(input_path), refresh=args.refresh)

    print("\n✅ Ingestion completed")
    print(f"Cases processed: {stats.get('cases_processed', 0)}")
    print(f"Chunks created: {stats.get('chunks_created', 0)}")
    print(f"Embeddings generated: {stats.get('embeddings_generated', 0)}")
    print(f"Qdrant stored: {stats.get('qdrant_stored', 0)}")
    print(f"Neo4j nodes created: {stats.get('neo4j_nodes_created', 0)}")
    print(f"Neo4j relations created: {stats.get('neo4j_relations_created', 0)}")
    print(f"Errors: {stats.get('errors', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
