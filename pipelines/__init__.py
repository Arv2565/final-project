"""
Pipelines module for Legal AI Assistant.

Contains all data ingestion, document processing, graph indexing,
vector indexing, and entity resolution pipelines.

Submodules:
- document_ingestion: PDF/JSON document extraction, chunking, preprocessing
- graph_index: GraphRAG triple extraction, canonicalization, Neo4j indexing
- vector_index: Vector embedding and Qdrant indexing management
- entity_resolution: Entity deduplication and resolution utilities
- cli: Command-line interfaces for all pipeline operations
"""
