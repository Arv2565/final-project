#!/usr/bin/env python3
"""
GraphRAG indexing CLI.

Examples:
  python scripts/graph_rag_index.py --paths data --recursive
  python scripts/graph_rag_index.py --paths data/knowledge_base --max-chunks 10

Requires env vars: OPENAI_API_KEY, NEO4J_PASSWORD (and NEO4J_URI/NEO4J_USER if non-default)
"""
import argparse
import os
import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from workflows.graphs import GraphRAGIndexer  # noqa: E402
from database.neo4j.client import close_neo4j_driver  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="GraphRAG indexer for JSON files -> Neo4j")
    parser.add_argument(
        "--paths",
        nargs="+",
        default=[str(PROJECT_ROOT / "data")],
        help="File or directory paths to process (default: data)",
    )
    parser.add_argument("--recursive", action="store_true", default=True, help="Recurse into subdirectories")
    parser.add_argument("--no-embed", action="store_true", help="Skip OpenAI embeddings for entities")
    parser.add_argument("--max-chunks", type=int, default=None, help="Cap chunks per file (for testing)")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set")
        sys.exit(1)
    if not os.getenv("NEO4J_PASSWORD"):
        print("NEO4J_PASSWORD not set")
        sys.exit(1)

    indexer = GraphRAGIndexer(create_vector_index=True)
    stats = indexer.index_json_files(
        paths=[Path(p) for p in args.paths],
        recursive=args.recursive,
        max_chunks_per_file=args.max_chunks,
        embed_entities=not args.no_embed,
    )

    print(
        f"Indexed files={stats.files_processed}, chunks={stats.chunks_processed}, "
        f"triples={stats.triples_extracted}, embedded_nodes={stats.nodes_embedded}"
    )
    close_neo4j_driver()


if __name__ == "__main__":
    main()
