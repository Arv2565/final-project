#!/usr/bin/env python3
"""
GraphRAG indexing CLI for JSON/TXT/PDF -> Neo4j.

Examples:
  python scripts/graph_rag_index.py --paths data --recursive
  python scripts/graph_rag_index.py --paths data/knowledge_base --max-chunks 10

Requires env vars: OPENAI_API_KEY, NEO4J_PASSWORD (and NEO4J_URI/NEO4J_USER if non-default)
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from workflows.graphs import GraphRAGIndexer  # noqa: E402
from database.neo4j.client import close_neo4j_driver  # noqa: E402


def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
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
        logger.error("OPENAI_API_KEY not set")
        sys.exit(1)
    if not os.getenv("NEO4J_PASSWORD"):
        logger.error("NEO4J_PASSWORD not set")
        sys.exit(1)

    # Check and log paths
    paths = [Path(p) for p in args.paths]
    logger.info(f"Processing paths: {paths}")
    
    for path in paths:
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            continue
        logger.info(f"Path exists: {path} (is_dir={path.is_dir()}, is_file={path.is_file()})")
        
        if path.is_dir():
            # Find files in directory
            if args.recursive:
                files = list(path.rglob('*'))
            else:
                files = list(path.iterdir())
            
            json_files = [f for f in files if f.suffix.lower() in ['.json', '.txt', '.pdf'] and f.is_file()]
            logger.info(f"Found {len(json_files)} processable files in {path}: {[f.name for f in json_files]}")
        elif path.is_file():
            logger.info(f"Single file to process: {path}")

    try:
        indexer = GraphRAGIndexer(create_vector_index=True)
        logger.info("GraphRAGIndexer created successfully")
        
        stats = indexer.index_json_files(
            paths=paths,
            recursive=args.recursive,
            max_chunks_per_file=args.max_chunks,
            embed_entities=not args.no_embed,
        )
    except Exception as e:
        logger.error(f"Error during indexing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    print(
        f"Indexed files={stats.files_processed}, chunks={stats.chunks_processed}, "
        f"triples={stats.triples_extracted}, embedded_nodes={stats.nodes_embedded}"
    )
    close_neo4j_driver()


if __name__ == "__main__":
    main()
