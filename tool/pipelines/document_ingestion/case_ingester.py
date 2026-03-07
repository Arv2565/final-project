"""
Case Data Ingestion Pipeline for Case Retrieval Module.

This module handles the end-to-end process of:
1. Reading case data from casefiles.json
2. Generating LLM-powered case descriptions (replaces semantic chunking)
3. Embedding generation from LLM descriptions (one vector per case)
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
from src.services.llm_case_summarizer import get_case_summarizer

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
    - LLM-powered case description generation
    - Embedding generation
    - Graph node creation
    - Relationship inference
    """
    
    def __init__(self):
        """Initialize pipeline with database managers and LLM summarizer."""
        self.qdrant_manager = QdrantCaseCollectionManager()
        self.neo4j_schema = CaseGraphSchema()
        self.embedding_service = InLegalBERTEmbeddingService()
        self.case_summarizer = get_case_summarizer()
        
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
            citation = metadata.get("citation", "")
            
            # Generate canonical case_id from normalized citation
            case_id = self._generate_case_id(citation)
            
            if not case_id:
                logger.warning("Case without citation, skipping")
                return
            
            # Determine court level
            court_level = get_court_level(
                metadata.get("court"),
                case.get("ratio", {}).get("text", "")
            ).value
            
            # Create Case node in Neo4j (with holding from top-level, not metadata)
            self._create_case_node(case_id, case, metadata, court_level)
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
            
            # Infer and create appellate/precedent relationships
            self._infer_and_link_relationships(case_id, case, metadata)
            
            # Generate LLM description for the case (optimized for vector search)
            llm_description = self._generate_llm_case_description(case)
            
            # Create single chunk from LLM description and embed
            case_vectors = self._generate_embedding_from_llm_description(
                llm_description, case_id, case, metadata, court_level
            )
            
            # Store in Qdrant
            stored_count = self.qdrant_manager.store_case_chunks(case_vectors)
            self.stats["qdrant_stored"] += stored_count
            
            logger.debug(f"Successfully processed case {case_id}: {len(case_vectors)} vectors stored")
        
        except Exception as e:
            logger.error(f"Error processing case: {e}")
            raise
    
    def _create_case_node(self, case_id: str, case: Dict[str, Any], metadata: Dict[str, Any], court_level: int):
        """Create Case node in Neo4j with proper holding extraction."""
        try:
            # Use top-level holding, not metadata.holding
            holding = case.get("holding", {}) or {}
            decision = holding.get("decision", "")
            has_reversal = "reversal" in decision.lower() or "reversed" in decision.lower()
            
            self.neo4j_schema.create_case_node(
                case_id=case_id,
                citation=metadata.get("citation", ""),
                date=metadata.get("date", ""),
                court=metadata.get("court", ""),
                court_level=court_level,
                case_type=self._normalize_case_type(case.get("case_type", "Unknown")),
                parties_appellant=metadata.get("parties_appellant"),
                parties_respondent=metadata.get("parties_respondent"),
                decision=decision,
                relief=holding.get("relief", ""),
                has_reversal=has_reversal
            )
            self.stats["neo4j_nodes_created"] += 1
        except Exception as e:
            logger.warning(f"Failed to create case node: {e}")
    
    def _create_issue_node_and_link(self, case_id: str, issue: Dict[str, Any]):
        """Create Issue node and link to case with normalized fields."""
        try:
            issue_id = issue.get("issue_id", "")
            if not issue_id:
                return
            
            # Normalize categorical fields
            legal_domain = self._normalize_legal_domain(issue.get("legal_domain", ""))
            outcome = self._normalize_issue_outcome(issue.get("outcome"))
            
            self.neo4j_schema.create_issue_node(
                issue_id=issue_id,
                description=issue.get("natural_form", ""),
                legal_domain=legal_domain,
                outcome=outcome
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
            
            # Link to case with section parameter to avoid over-linking
            # (fixes bug where multiple sections of same statute could over-link)
            self.neo4j_schema.create_relationship(
                from_case_id=case_id,
                relationship_type=self.neo4j_schema.INTERPRETS_REL,
                to_node_id=statute_name,
                to_node_label=self.neo4j_schema.STATUTE_LABEL,
                to_section=section,
                properties={"section": section}
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
    
    def _generate_llm_case_description(self, case: Dict[str, Any]) -> str:
        """
        Generate LLM-powered semantic description for the case.
        
        Args:
            case: Complete case JSON from casefiles.json
        
        Returns:
            Semantic description optimized for vector search
        """
        try:
            logger.debug(f"Generating LLM description for case: {case.get('metadata', {}).get('citation', 'Unknown')}")
            description = self.case_summarizer.generate_case_description(case)
            self.stats["chunks_created"] += 1
            return description
        except Exception as e:
            logger.error(f"Failed to generate LLM description: {e}")
            # Return fallback: concatenation of key fields
            return self._generate_fallback_description(case)
    
    def _generate_fallback_description(self, case: Dict[str, Any]) -> str:
        """Generate fallback description if LLM fails."""
        metadata = case.get("metadata", {})
        issues = case.get("issues", [])
        holding = case.get("holding", {}) or {}
        
        parts = []
        parts.append(f"Case: {metadata.get('citation', 'Unknown')}")
        
        if issues:
            issue_texts = [i.get("natural_form", "") for i in issues[:3]]
            parts.append(f"Issues: {'; '.join(filter(None, issue_texts))}")
        
        if holding:
            decision = holding.get("decision", "")
            relief = holding.get("relief", "")
            if decision or relief:
                parts.append(f"Decision: {decision}. Relief: {relief}")
        
        legal_concepts = case.get("legal_concepts", [])
        if legal_concepts:
            parts.append(f"Legal Concepts: {', '.join(legal_concepts[:10])}")
        
        return " ".join(parts)
    
    def _generate_embedding_from_llm_description(
        self,
        llm_description: str,
        case_id: str,
        case: Dict[str, Any],
        metadata: Dict[str, Any],
        court_level: int
    ) -> List[CaseVector]:
        """
        Create single embedding from LLM description.
        
        Args:
            llm_description: LLM-generated case description
            case_id: Normalized case identifier
            case: Full case data
            metadata: Case metadata
            court_level: Court level (1=Supreme, 2=High, 3=Lower)
        
        Returns:
            List with single CaseVector containing the embedding
        """
        try:
            # Generate embedding for the LLM description
            embedding_result = self.embedding_service.generate_embeddings([llm_description])
            self.stats["embeddings_generated"] += 1
            
            if embedding_result.embeddings is None or embedding_result.embeddings.size == 0:
                logger.error("No embedding generated for case description")
                return []
            
            # Create metadata payload
            base_metadata = {
                "citation": metadata.get("citation", ""),
                "court": metadata.get("court", ""),
                "court_level": court_level,
                "date": metadata.get("date", ""),
                "year": int(metadata.get("date", "")[:4]) if metadata.get("date") else None,
                "legal_concepts": case.get("legal_concepts", []),
                "statutes_mentioned": [s.get("statute_name", "") for s in case.get("statutes_interpreted", [])],
                "content_type": "llm_description",
                "decision": case.get("holding", {}).get("decision", "") if case.get("holding") else "",
                "relief_type": case.get("holding", {}).get("relief", "") if case.get("holding") else "",
                "pdf_path": case.get("evidence", {}).get("pdf_path", "") if case.get("evidence") else "",
            }
            
            # Create single CaseVector from LLM description
            case_vector = CaseVector(
                case_id=case_id,
                chunk_id=0,
                total_chunks=1,
                chunk_text=llm_description,
                embedding=embedding_result.embeddings[0],
                content_type="llm_description",
                metadata=base_metadata
            )
            
            logger.debug(f"Created single embedding for case {case_id} from LLM description")
            return [case_vector]
        
        except Exception as e:
            logger.error(f"Failed to generate embedding from LLM description: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
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
            embedding_result = self.embedding_service.generate_embeddings(texts)
            
            self.stats["embeddings_generated"] += len(texts)
            
            # Create CaseVector objects
            case_vectors = []
            for chunk, embedding in zip(chunks, embedding_result.embeddings):
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
    
    def _generate_case_id(self, citation: str) -> str:
        """
        Generate canonical case ID from citation.
        
        Normalizes citation to create stable, unique identifier.
        """
        if not citation:
            return ""
        # Normalize: remove punctuation/spaces, convert to lowercase
        canonical = citation.replace(" ", "_").replace(".", "_").replace(",", "_").lower()
        # Remove consecutive underscores
        while "__" in canonical:
            canonical = canonical.replace("__", "_")
        # Truncate to reasonable length
        return canonical[:150]
    
    def _normalize_legal_domain(self, domain: str) -> str:
        """
        Normalize legal domain field to enum-like values.
        
        Handles space/underscore variants.
        """
        if not domain:
            return "general"
        # Standardize to lowercase with underscores
        normalized = domain.lower().replace(" ", "_").replace("-", "_")
        return normalized
    
    def _normalize_case_type(self, case_type: str) -> str:
        """Normalize case type field."""
        if not case_type:
            return "Unknown"
        return case_type.strip().title()
    
    def _normalize_issue_outcome(self, outcome: Optional[str]) -> Optional[str]:
        """Normalize issue outcome field."""
        if not outcome:
            return None
        normalized = outcome.lower().replace(" ", "_").replace("-", "_")
        return normalized if normalized else None
    
    def _infer_and_link_relationships(self, case_id: str, case: Dict[str, Any], metadata: Dict[str, Any]):
        """
        Infer and create appellate/precedent relationships with confidence tracking.
        
        Uses existing inference utilities to populate CITES and APPEALS_FROM edges.
        """
        try:
            citation = metadata.get("citation", "")
            if not citation:
                return
            
            # Infer case hierarchy (appellate chain)
            try:
                hierarchy = infer_case_hierarchy(case)
                if hierarchy and isinstance(hierarchy, dict):
                    # Extract appeal_from if present and confidence is high
                    appeal_from = hierarchy.get("appeal_from")
                    confidence = hierarchy.get("confidence", 0.0)
                    
                    if appeal_from and confidence >= 0.6:
                        # Create APPEALS_FROM relationship
                        appeal_case_id = self._generate_case_id(appeal_from)
                        if appeal_case_id:
                            self.neo4j_schema.create_relationship(
                                from_case_id=case_id,
                                relationship_type=self.neo4j_schema.APPEALS_FROM_REL,
                                to_node_id=appeal_case_id,
                                to_node_label=self.neo4j_schema.CASE_LABEL,
                                properties={"confidence": confidence, "extraction_method": "infer_case_hierarchy"}
                            )
                            self.stats["neo4j_relations_created"] += 1
                            logger.debug(f"Created APPEALS_FROM relationship with confidence {confidence}")
            except Exception as e:
                logger.debug(f"Hierarchy inference skipped: {e}")
            
            # Infer reversal status
            try:
                reversal = detect_reversal_status(case)
                if reversal and isinstance(reversal, dict):
                    reversal_status = reversal.get("reversal_status")
                    confidence = reversal.get("confidence", 0.0)
                    
                    # Note: CITES relationships require precedent citations from case content
                    # For now, this stores reversal info on case properties
                    logger.debug(f"Detected reversal status: {reversal_status} (confidence: {confidence})")
            except Exception as e:
                logger.debug(f"Reversal detection skipped: {e}")
        
        except Exception as e:
            logger.warning(f"Relationship inference failed: {e}")
    
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
