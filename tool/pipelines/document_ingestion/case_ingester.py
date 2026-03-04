"""
Case Data Ingestion Pipeline for Case Retrieval Module.

This module handles the end-to-end process of:
1. Reading case data from casefiles.json
2. Semantic chunking (issue, ratio, statute, holding)
3. Embedding generation
4. Storage in Qdrant and Neo4j
5. Metadata extraction and indexing
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.database.qdrant.case_collection import QdrantCaseCollectionManager, CaseVector, get_chunk_config
from src.database.neo4j.case_schema import CaseGraphSchema
from src.database.embeddings import InLegalBERTEmbeddingService
from src.utils.court_hierarchy import get_court_level, CourtLevel
from src.utils.case_relationships import infer_case_hierarchy, detect_reversal_status

logger = logging.getLogger(__name__)


class CaseChunk:
    """Represents a single semantic chunk from a case."""
    
    def __init__(
        self,
        case_id: str,
        chunk_id: int,
        total_chunks: int,
        content_type: str,  # issue, ratio, statute, holding
        text: str,
        metadata: Dict[str, Any]
    ):
        self.case_id = case_id
        self.chunk_id = chunk_id
        self.total_chunks = total_chunks
        self.content_type = content_type
        self.text = text
        self.metadata = metadata


class CaseIngestionPipeline:
    """
    Pipeline for ingesting case data into Qdrant and Neo4j.
    
    Orchestrates:
    - JSON reading and validation
    - Semantic chunking
    - Embedding generation
    - Graph node creation
    - Relationship inference
    """
    
    def __init__(self):
        """Initialize pipeline with database managers."""
        self.qdrant_manager = QdrantCaseCollectionManager()
        self.neo4j_schema = CaseGraphSchema()
        self.embedding_service = InLegalBERTEmbeddingService()
        
        self.stats = {
            "cases_processed": 0,
            "chunks_created": 0,
            "embeddings_generated": 0,
            "qdrant_stored": 0,
            "neo4j_nodes_created": 0,
            "neo4j_relations_created": 0,
            "errors": 0,
        }
    
    def ingest_from_file(self, filepath: str, refresh: bool = False) -> Dict[str, Any]:
        """
        Ingestion entry point: Read cases from JSON file and store in databases.
        
        Args:
            filepath: Path to casefiles.json
            refresh: If True, clear existing collections before ingesting
        
        Returns:
            Dictionary with ingestion statistics
        """
        try:
            # Optionally clear existing data
            if refresh:
                logger.warning("Clearing existing case collections...")
                self.qdrant_manager.delete_collection()
                # Note: Neo4j clearing would require more careful handling
            
            # Read case file
            logger.info(f"Reading cases from {filepath}")
            cases = self._read_cases_from_file(filepath)
            logger.info(f"Loaded {len(cases)} cases from file")
            
            # Process each case
            for i, case in enumerate(cases):
                try:
                    self._process_case(case)
                    self.stats["cases_processed"] += 1
                    
                    if (i + 1) % 5 == 0:
                        logger.info(f"Processed {i + 1}/{len(cases)} cases...")
                
                except Exception as e:
                    logger.error(f"Error processing case {i}: {e}")
                    self.stats["errors"] += 1
            
            logger.info("Case ingestion completed")
            self._print_statistics()
            return self.stats
        
        except Exception as e:
            logger.error(f"Case ingestion pipeline failed: {e}")
            raise RuntimeError(f"Ingestion failed: {e}")
    
    def _read_cases_from_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Read and validate cases from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                cases = json.load(f)
            
            if not isinstance(cases, list):
                raise ValueError("casefiles.json root must be an array")
            
            logger.info(f"Successfully loaded {len(cases)} cases from JSON")
            return cases
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise RuntimeError(f"Invalid JSON file: {e}")
        except Exception as e:
            logger.error(f"Error reading case file: {e}")
            raise RuntimeError(f"Cannot read file: {e}")
    
    def _process_case(self, case: Dict[str, Any]):
        """Process a single case: chunk, embed, and store."""
        try:
            # Extract metadata
            metadata = case.get("metadata", {})
            case_id = metadata.get("citation", "").replace(" ", "_").replace(".", "_")
            
            if not case_id:
                logger.warning("Case without citation, skipping")
                return
            
            # Determine court level
            court_level = get_court_level(
                metadata.get("court"),
                case.get("ratio", {}).get("text", "")
            ).value
            
            # Create Case node in Neo4j
            self._create_case_node(case_id, metadata, court_level)
            self.stats["neo4j_nodes_created"] += 1
            
            # Create issue nodes and link to case
            issues = case.get("issues", [])
            for issue in issues:
                self._create_issue_node_and_link(case_id, issue)
            
            # Create statute nodes and link to case
            statutes = case.get("statutes_interpreted", [])
            for statute in statutes:
                self._create_statute_node_and_link(case_id, statute)
            
            # Create judge nodes and link to case
            judges = metadata.get("bench", [])
            for judge_name in judges:
                self._create_judge_node_and_link(case_id, judge_name, metadata.get("court"))
            
            # Create semantic chunks and embed
            chunks = self._create_semantic_chunks(case_id, case, metadata, court_level)
            
            # Generate embeddings for chunks
            case_vectors = self._generate_embeddings_for_chunks(chunks, metadata, case_id)
            
            # Store in Qdrant
            stored_count = self.qdrant_manager.store_case_chunks(case_vectors)
            self.stats["qdrant_stored"] += stored_count
            
            logger.debug(f"Successfully processed case {case_id}: {len(chunks)} chunks, {stored_count} stored")
        
        except Exception as e:
            logger.error(f"Error processing case: {e}")
            raise
    
    def _create_case_node(self, case_id: str, metadata: Dict[str, Any], court_level: int):
        """Create Case node in Neo4j."""
        try:
            holding = metadata.get("holding", {}) or {}
            decision = holding.get("decision", "")
            has_reversal = "reversal" in decision.lower() or "reversed" in decision.lower()
            
            self.neo4j_schema.create_case_node(
                case_id=case_id,
                citation=metadata.get("citation", ""),
                date=metadata.get("date", ""),
                court=metadata.get("court", ""),
                court_level=court_level,
                case_type="Unknown",  # Could infer from legal_concepts or issues
                parties_appellant=None,
                parties_respondent=None,
                decision=decision,
                relief=holding.get("relief", ""),
                has_reversal=has_reversal
            )
            self.stats["neo4j_nodes_created"] += 1
        except Exception as e:
            logger.warning(f"Failed to create case node: {e}")
    
    def _create_issue_node_and_link(self, case_id: str, issue: Dict[str, Any]):
        """Create Issue node and link to case."""
        try:
            issue_id = issue.get("issue_id", "")
            if not issue_id:
                return
            
            self.neo4j_schema.create_issue_node(
                issue_id=issue_id,
                description=issue.get("natural_form", ""),
                legal_domain=issue.get("legal_domain", ""),
                outcome=issue.get("outcome")
            )
            self.stats["neo4j_nodes_created"] += 1
            
            # Link to case
            self.neo4j_schema.create_relationship(
                from_case_id=case_id,
                relationship_type=self.neo4j_schema.RAISES_REL,
                to_node_id=issue_id,
                to_node_label=self.neo4j_schema.ISSUE_LABEL
            )
            self.stats["neo4j_relations_created"] += 1
        except Exception as e:
            logger.warning(f"Failed to create issue node: {e}")
    
    def _create_statute_node_and_link(self, case_id: str, statute: Dict[str, Any]):
        """Create Statute node and link to case."""
        try:
            statute_name = statute.get("statute_name", "")
            section = statute.get("section", "")
            
            if not statute_name:
                return
            
            self.neo4j_schema.create_statute_node(
                statute_name=statute_name,
                section=section,
                interpretation_summary=statute.get("interpretation", "")
            )
            self.stats["neo4j_nodes_created"] += 1
            
            # Link to case
            self.neo4j_schema.create_relationship(
                from_case_id=case_id,
                relationship_type=self.neo4j_schema.INTERPRETS_REL,
                to_node_id=statute_name,
                to_node_label=self.neo4j_schema.STATUTE_LABEL,
                properties={"section": section, "date": ""}  # date from case metadata
            )
            self.stats["neo4j_relations_created"] += 1
        except Exception as e:
            logger.warning(f"Failed to create statute node: {e}")
    
    def _create_judge_node_and_link(self, case_id: str, judge_name: str, court: Optional[str] = None):
        """Create Judge node and link to case."""
        try:
            if not judge_name or not judge_name.strip():
                return
            
            # Clean up judge name (remove titles like "J.", "CJI", etc.)
            clean_name = judge_name.replace(", J.", "").replace(" J.", "").strip()
            
            if not clean_name:
                return
            
            self.neo4j_schema.create_judge_node(clean_name, court)
            self.stats["neo4j_nodes_created"] += 1
            
            # Link to case
            self.neo4j_schema.create_relationship(
                from_case_id=case_id,
                relationship_type=self.neo4j_schema.DECIDED_BY_REL,
                to_node_id=clean_name,
                to_node_label=self.neo4j_schema.JUDGE_LABEL
            )
            self.stats["neo4j_relations_created"] += 1
        except Exception as e:
            logger.warning(f"Failed to create judge node: {e}")
    
    def _create_semantic_chunks(
        self,
        case_id: str,
        case: Dict[str, Any],
        metadata: Dict[str, Any],
        court_level: int
    ) -> List[CaseChunk]:
        """
        Create semantic chunks from case data.
        
        Chunks are organized by: issue, ratio/reasoning, statute interpretation, holding
        """
        chunks = []
        chunk_id = 0
        
        # Base metadata shared across all chunks
        base_metadata = {
            "citation": metadata.get("citation", ""),
            "court": metadata.get("court", ""),
            "court_level": court_level,
            "date": metadata.get("date", ""),
            "year": int(metadata.get("date", "")[:4]) if metadata.get("date") else None,
            "legal_concepts": case.get("legal_concepts", []),
            "statutes_mentioned": [s.get("statute_name", "") for s in case.get("statutes_interpreted", [])],
        }
        
        # Chunk 1: Issues
        for issue in case.get("issues", []):
            issue_text = f"Issue: {issue.get('natural_form', '')}\nOutcome: {issue.get('outcome', '')}"
            
            chunk_metadata = {
                **base_metadata,
                "content_type": "issue",
                "legal_domain": issue.get("legal_domain", ""),
                "issue_id": issue.get("issue_id", ""),
                "decision": issue.get("outcome", ""),
            }
            
            chunks.append(CaseChunk(
                case_id=case_id,
                chunk_id=chunk_id,
                total_chunks=len([c for c in case.get("issues", [])] or [0]),
                content_type="issue",
                text=issue_text,
                metadata=chunk_metadata
            ))
            chunk_id += 1
        
        # Chunk 2: Ratio/Reasoning
        ratio = case.get("ratio", {}) or {}
        ratio_text = ratio.get("text", "")
        
        if ratio_text:
            chunk_metadata = {
                **base_metadata,
                "content_type": "ratio",
                "section": ratio.get("source_hint", {}).get("section", ""),
            }
            
            chunks.append(CaseChunk(
                case_id=case_id,
                chunk_id=chunk_id,
                total_chunks=len(case.get("statutes_interpreted", []) or [0]) + 1,
                content_type="ratio",
                text=ratio_text,
                metadata=chunk_metadata
            ))
            chunk_id += 1
        
        # Chunk 3: Statute Interpretations
        for statute in case.get("statutes_interpreted", []):
            statute_text = (
                f"Statute: {statute.get('statute_name', '')}\n"
                f"Section: {statute.get('section', '')}\n"
                f"Interpretation: {statute.get('interpretation', '')}"
            )
            
            chunk_metadata = {
                **base_metadata,
                "content_type": "statute",
                "statute_name": statute.get("statute_name", ""),
                "section": statute.get("section", ""),
                "relief_type": case.get("holding", {}).get("relief", "") if case.get("holding") else "",
            }
            
            chunks.append(CaseChunk(
                case_id=case_id,
                chunk_id=chunk_id,
                total_chunks=len(case.get("statutes_interpreted", []) or [0]),
                content_type="statute",
                text=statute_text,
                metadata=chunk_metadata
            ))
            chunk_id += 1
        
        # Chunk 4: Holding/Decision
        holding = case.get("holding", {}) or {}
        holding_text = f"Decision: {holding.get('decision', '')}\nRelief: {holding.get('relief', '')}"
        
        if holding_text.strip() != "Decision: \nRelief: ":
            chunk_metadata = {
                **base_metadata,
                "content_type": "holding",
                "decision": holding.get("decision", ""),
                "relief_type": holding.get("relief", ""),
            }
            
            chunks.append(CaseChunk(
                case_id=case_id,
                chunk_id=chunk_id,
                total_chunks=1,
                content_type="holding",
                text=holding_text,
                metadata=chunk_metadata
            ))
        
        self.stats["chunks_created"] += len(chunks)
        logger.debug(f"Created {len(chunks)} semantic chunks for case {case_id}")
        
        return chunks
    
    def _generate_embeddings_for_chunks(
        self,
        chunks: List[CaseChunk],
        metadata: Dict[str, Any],
        case_id: str
    ) -> List[CaseVector]:
        """Generate embeddings for case chunks."""
        try:
            # Batch embed chunk texts
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.embed_texts(texts)
            
            self.stats["embeddings_generated"] += len(texts)
            
            # Create CaseVector objects
            case_vectors = []
            for chunk, embedding in zip(chunks, embeddings):
                case_vector = CaseVector(
                    case_id=case_id,
                    chunk_id=chunk.chunk_id,
                    total_chunks=chunk.total_chunks,
                    chunk_text=chunk.text,
                    embedding=embedding,
                    content_type=chunk.content_type,
                    metadata=chunk.metadata
                )
                case_vectors.append(case_vector)
            
            return case_vectors
        
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def _print_statistics(self):
        """Print ingestion statistics."""
        logger.info("=" * 60)
        logger.info("CASE INGESTION STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Cases processed:        {self.stats['cases_processed']}")
        logger.info(f"Chunks created:         {self.stats['chunks_created']}")
        logger.info(f"Embeddings generated:   {self.stats['embeddings_generated']}")
        logger.info(f"Qdrant chunks stored:   {self.stats['qdrant_stored']}")
        logger.info(f"Neo4j nodes created:    {self.stats['neo4j_nodes_created']}")
        logger.info(f"Neo4j relations:        {self.stats['neo4j_relations_created']}")
        logger.info(f"Errors encountered:     {self.stats['errors']}")
        logger.info("=" * 60)
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.neo4j_schema.close()
            logger.info("Pipeline cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
