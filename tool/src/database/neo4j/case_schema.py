"""
Neo4j Case Schema Definition for Case Retrieval Module.

This module manages the Neo4j graph schema specifically for case relationships,
independent from the existing legal documents graph.

Defines:
- Case nodes and their properties
- Issue, statute, judge nodes
- Relationships between cases (appellate, precedent, citation)
- Graph constraints and indexes for query efficiency
"""

import logging
from typing import Dict, List, Optional, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from neo4j import GraphDatabase, Result, Session, Transaction
    from neo4j.exceptions import ClientError, ServiceUnavailable
except ImportError:
    raise ImportError("neo4j is required. Install with: pip install neo4j")

from src.config import get_settings

logger = logging.getLogger(__name__)


class CaseGraphSchema:
    """
    Manages Neo4j schema for legal cases.
    
    Defines node types, relationships, constraints, and indexes specifically
    for the case retrieval module's graph database.
    
    Supports canonical case identity with citation aliases to handle
    multi-citation real-world cases.
    """
    
    # Node labels
    CASE_LABEL = "Case"
    ISSUE_LABEL = "CaseIssue"
    STATUTE_LABEL = "CaseStatute"
    JUDGE_LABEL = "CaseJudge"
    
    # Relationship types
    RAISES_REL = "RAISES"  # Case raises an issue
    INTERPRETS_REL = "INTERPRETS"  # Case interprets a statute
    DECIDED_BY_REL = "DECIDED_BY"  # Case decided by judge/bench
    CITES_REL = "CITES"  # Case cites another case (precedent)
    APPEALS_FROM_REL = "APPEALS_FROM"  # Case is appeal from another case
    REMANDED_TO_REL = "REMANDED_TO"  # Case remanded to another court
    
    def __init__(self):
        """Initialize Neo4j connection and ensure schema exists."""
        self.settings = get_settings()
        self.driver = self._create_driver()
        self._relationship_types_cache: Optional[set[str]] = None
        self._ensure_schema_exists()

    def _get_relationship_types(self) -> set[str]:
        """Fetch and cache available relationship types in the current database."""
        if self._relationship_types_cache is not None:
            return self._relationship_types_cache

        try:
            with self.driver.session() as session:
                result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
                self._relationship_types_cache = {record["relationshipType"] for record in result}
        except Exception as e:
            logger.warning(f"Could not read Neo4j relationship types: {e}")
            self._relationship_types_cache = set()

        return self._relationship_types_cache
    
    def _create_driver(self):
        """Create Neo4j driver connection."""
        try:
            driver = GraphDatabase.driver(
                self.settings.neo4j.uri,
                auth=(self.settings.neo4j.user, self.settings.neo4j.password)
            )
            
            # Test connection
            with driver.session() as session:
                result = session.run("RETURN 1 as ping")
                list(result)
            
            logger.info(f"Connected to Neo4j at {self.settings.neo4j.uri}")
            return driver
            
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise ConnectionError(f"Cannot connect to Neo4j: {e}")
        except Exception as e:
            logger.error(f"Failed to create Neo4j driver: {e}")
            raise RuntimeError(f"Neo4j connection failed: {e}")
    
    def _ensure_schema_exists(self):
        """Ensure all schema elements exist in the database."""
        try:
            with self.driver.session() as session:
                # Create constraints
                self._create_constraints(session)
                
                # Create indexes
                self._create_indexes(session)
            
            logger.info("Neo4j case schema verified and initialized")
            
        except Exception as e:
            logger.error(f"Failed to ensure schema exists: {e}")
            raise RuntimeError(f"Schema initialization failed: {e}")
    
    def _create_constraints(self, session: Session):
        """Create uniqueness constraints for case nodes."""
        constraints = [
            # Case uniqueness (canonical case_id only)
            f"CREATE CONSTRAINT case_id_unique IF NOT EXISTS "
            f"FOR (c:{self.CASE_LABEL}) REQUIRE c.case_id IS UNIQUE",
            
            # Note: Citation is indexed but not unique to allow citation aliases
            # for cases with multiple valid citations
            
            # Judge uniqueness
            f"CREATE CONSTRAINT judge_name_unique IF NOT EXISTS "
            f"FOR (j:{self.JUDGE_LABEL}) REQUIRE j.name IS UNIQUE",
            
            # Issue uniqueness
            f"CREATE CONSTRAINT issue_id_unique IF NOT EXISTS "
            f"FOR (i:{self.ISSUE_LABEL}) REQUIRE i.issue_id IS UNIQUE",
        ]
        
        for constraint_query in constraints:
            try:
                session.run(constraint_query)
                logger.debug(f"Constraint verified: {constraint_query[:50]}...")
            except ClientError as e:
                if "already exists" in str(e).lower():
                    logger.debug(f"Constraint already exists")
                else:
                    logger.warning(f"Constraint creation failed: {e}")
    
    def _create_indexes(self, session: Session):
        """Create indexes for efficient querying."""
        indexes = [
            # Case indexes
            f"CREATE INDEX case_citation IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.citation)",
            f"CREATE INDEX case_citation_normalized IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.citation_normalized)",
            f"CREATE INDEX case_date IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.date)",
            f"CREATE INDEX case_court IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.court)",
            f"CREATE INDEX case_court_level IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.court_level)",
            f"CREATE INDEX case_year IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.year)",
            f"CREATE INDEX case_type IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.case_type)",
            f"CREATE INDEX case_decision IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.decision)",
            f"CREATE INDEX case_has_reversal IF NOT EXISTS FOR (c:{self.CASE_LABEL}) ON (c.has_reversal)",
            
            # Issue indexes
            f"CREATE INDEX issue_legal_domain IF NOT EXISTS FOR (i:{self.ISSUE_LABEL}) ON (i.legal_domain)",
            f"CREATE INDEX issue_outcome IF NOT EXISTS FOR (i:{self.ISSUE_LABEL}) ON (i.outcome)",
            
            # Statute indexes (composite for statute+section lookup)
            f"CREATE INDEX statute_name IF NOT EXISTS FOR (s:{self.STATUTE_LABEL}) ON (s.statute_name)",
            f"CREATE INDEX statute_name_section IF NOT EXISTS FOR (s:{self.STATUTE_LABEL}) ON (s.statute_name, s.section)",
        ]
        
        for index_query in indexes:
            try:
                session.run(index_query)
                logger.debug(f"Index verified: {index_query[:50]}...")
            except ClientError as e:
                if "already exists" in str(e).lower():
                    logger.debug(f"Index already exists")
                else:
                    logger.warning(f"Index creation failed: {e}")
    
    def create_case_node(
        self,
        case_id: str,
        citation: str,
        date: str,
        court: str,
        court_level: int,
        case_type: str,
        parties_appellant: Optional[str] = None,
        parties_respondent: Optional[str] = None,
        decision: Optional[str] = None,
        relief: Optional[str] = None,
        has_reversal: bool = False,
        citation_aliases: Optional[List[str]] = None
    ) -> bool:
        """
        Create a Case node in the graph with support for citation aliases.
        
        Args:
            case_id: Unique case identifier (canonical)
            citation: Primary case citation (e.g., "(2000) 6 SCC 359")
            date: Judgment date (ISO format: YYYY-MM-DD)
            court: Court name
            court_level: 1=Supreme, 2=High, 3=Lower
            case_type: Criminal, Civil, Constitutional, etc.
            parties_appellant: Appellant name (optional)
            parties_respondent: Respondent name (optional)
            decision: Decision outcome
            relief: Relief granted
            has_reversal: Whether decision involves reversal
            citation_aliases: Alternative citations for same case (optional)
        
        Returns:
            True if created/updated successfully
        """
        try:
            with self.driver.session() as session:
                # Normalize citation for indexed lookups
                citation_normalized = self._normalize_citation(citation) if citation else ""
                
                query = f"""
                MERGE (c:{self.CASE_LABEL} {{case_id: $case_id}})
                SET 
                    c.citation = $citation,
                    c.citation_normalized = $citation_normalized,
                    c.citation_aliases = $citation_aliases,
                    c.date = $date,
                    c.court = $court,
                    c.court_level = $court_level,
                    c.case_type = $case_type,
                    c.parties_appellant = $parties_appellant,
                    c.parties_respondent = $parties_respondent,
                    c.decision = $decision,
                    c.relief = $relief,
                    c.has_reversal = $has_reversal,
                    c.year = $year,
                    c.created_at = datetime()
                RETURN c.case_id as created_case_id
                """
                
                year = int(date.split("-")[0]) if date else None
                aliases_normalized = [self._normalize_citation(c) for c in (citation_aliases or [])] if citation_aliases else []
                
                result = session.run(
                    query,
                    case_id=case_id,
                    citation=citation,
                    citation_normalized=citation_normalized,
                    citation_aliases=aliases_normalized,
                    date=date,
                    court=court,
                    court_level=court_level,
                    case_type=case_type,
                    parties_appellant=parties_appellant,
                    parties_respondent=parties_respondent,
                    decision=decision,
                    relief=relief,
                    has_reversal=has_reversal,
                    year=year
                )
                
                result_data = list(result)
                if result_data:
                    logger.debug(f"Created/updated Case node: {case_id}")
                    return True
                
                return False
        
        except Exception as e:
            logger.error(f"Failed to create case node: {e}")
            raise RuntimeError(f"Case node creation failed: {e}")
    
    def create_issue_node(
        self,
        issue_id: str,
        description: str,
        legal_domain: str,
        outcome: Optional[str] = None
    ) -> bool:
        """
        Create a CaseIssue node.
        
        Args:
            issue_id: Unique issue identifier
            description: Issue description
            legal_domain: Legal domain (criminal_law, service_law, etc.)
            outcome: Outcome (allowed, denied, clarified, etc.)
        
        Returns:
            True if created successfully
        """
        try:
            with self.driver.session() as session:
                query = f"""
                MERGE (i:{self.ISSUE_LABEL} {{issue_id: $issue_id}})
                SET 
                    i.description = $description,
                    i.legal_domain = $legal_domain,
                    i.outcome = $outcome,
                    i.created_at = datetime()
                RETURN i.issue_id as created_issue_id
                """
                
                result = session.run(
                    query,
                    issue_id=issue_id,
                    description=description,
                    legal_domain=legal_domain,
                    outcome=outcome
                )
                
                result_data = list(result)
                return bool(result_data)
        
        except Exception as e:
            logger.error(f"Failed to create issue node: {e}")
            raise RuntimeError(f"Issue node creation failed: {e}")
    
    def create_statute_node(
        self,
        statute_name: str,
        section: str,
        interpretation_summary: Optional[str] = None
    ) -> bool:
        """
        Create a CaseStatute node.
        
        Args:
            statute_name: Name of the statute/act
            section: Section/article number
            interpretation_summary: How statute was interpreted
        
        Returns:
            True if created successfully
        """
        try:
            with self.driver.session() as session:
                query = f"""
                MERGE (s:{self.STATUTE_LABEL} {{statute_name: $statute_name, section: $section}})
                SET 
                    s.interpretation_summary = $interpretation_summary,
                    s.created_at = datetime()
                RETURN s.statute_name as created_statute
                """
                
                result = session.run(
                    query,
                    statute_name=statute_name,
                    section=section,
                    interpretation_summary=interpretation_summary
                )
                
                result_data = list(result)
                return bool(result_data)
        
        except Exception as e:
            logger.error(f"Failed to create statute node: {e}")
            raise RuntimeError(f"Statute node creation failed: {e}")
    
    def create_judge_node(self, judge_name: str, court: Optional[str] = None) -> bool:
        """
        Create a CaseJudge node.
        
        Args:
            judge_name: Name of judge/justice
            court: Court where judge sits (optional)
        
        Returns:
            True if created successfully
        """
        try:
            with self.driver.session() as session:
                query = f"""
                MERGE (j:{self.JUDGE_LABEL} {{name: $judge_name}})
                SET 
                    j.court = $court,
                    j.created_at = datetime()
                RETURN j.name as created_judge
                """
                
                result = session.run(
                    query,
                    judge_name=judge_name,
                    court=court
                )
                
                result_data = list(result)
                return bool(result_data)
        
        except Exception as e:
            logger.error(f"Failed to create judge node: {e}")
            raise RuntimeError(f"Judge node creation failed: {e}")
    
    def create_relationship(
        self,
        from_case_id: str,
        relationship_type: str,
        to_node_id: str,
        to_node_label: str,
        properties: Optional[Dict[str, Any]] = None,
        to_section: Optional[str] = None
    ) -> bool:
        """
        Create a relationship between nodes.
        
        Args:
            from_case_id: Source case ID
            relationship_type: Type of relationship (RAISES, INTERPRETS, CITES, etc.)
            to_node_id: Target node ID
            to_node_label: Target node label (ISSUE_LABEL, STATUTE_LABEL, etc.)
            properties: Additional relationship properties with confidence/method
            to_section: Section (for statute relationships) to ensure correct linking
        
        Returns:
            True if created successfully
        """
        try:
            properties = properties or {}
            
            with self.driver.session() as session:
                # Build dynamic match clause based on label and relationship type
                if to_node_label == self.CASE_LABEL:
                    # For CITES/APPEALS_FROM: match by case_id
                    target_match = f"(t:{to_node_label} {{case_id: $to_node_id}})"
                elif to_node_label == self.JUDGE_LABEL:
                    target_match = f"(t:{to_node_label} {{name: $to_node_id}})"
                elif to_node_label == self.ISSUE_LABEL:
                    target_match = f"(t:{to_node_label} {{issue_id: $to_node_id}})"
                elif to_node_label == self.STATUTE_LABEL:
                    # For INTERPRETS: match by statute_name AND section to avoid over-linking
                    if to_section:
                        target_match = f"(t:{to_node_label} {{statute_name: $to_node_id, section: $to_section}})"
                    else:
                        target_match = f"(t:{to_node_label} {{statute_name: $to_node_id}})"
                else:
                    target_match = f"(t:{to_node_label} {{name: $to_node_id}})"
                
                query = f"""
                MATCH (c:{self.CASE_LABEL} {{case_id: $from_case_id}})
                MATCH {target_match}
                MERGE (c)-[r:{relationship_type}]->(t)
                SET r += $properties, r.created_at = coalesce(r.created_at, datetime())
                RETURN TYPE(r) as rel_type
                """
                
                result = session.run(
                    query,
                    from_case_id=from_case_id,
                    to_node_id=to_node_id,
                    to_section=to_section,
                    properties=properties
                )
                
                result_data = list(result)
                if result_data:
                    logger.debug(f"Created {relationship_type} relationship")
                    return True
                
                return False
        
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            logger.warning(f"This may be due to nodes not existing - ensure nodes are created first")
            return False
    
    def query_case_precedents(
        self,
        case_id: str,
        depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Query precedent chain for a given case.
        
        Traverses CITES relationships to find precedents.
        Returns relationship confidence for edge filtering.
        
        Args:
            case_id: Starting case ID
            depth: Maximum depth to traverse
        
        Returns:
            List of precedent cases with confidence metadata
        """
        try:
            if self.CITES_REL not in self._get_relationship_types():
                logger.debug(f"Skipping precedent traversal: relationship type '{self.CITES_REL}' not present")
                return []

            with self.driver.session() as session:
                query = f"""
                MATCH (c1:{self.CASE_LABEL} {{case_id: $case_id}})
                MATCH path = (c1)-[r:{self.CITES_REL}*1..{depth}]->(c2:{self.CASE_LABEL})
                WITH c2, path, [rel IN relationships(path) | coalesce(properties(rel)['confidence'], 1.0)] as confidences
                RETURN c2.citation as citation, c2.case_id as case_id, c2.date as date, c2.court as court, 
                       length(path) as distance, confidences[0] as confidence, 'graph_traversal' as extraction_method
                ORDER BY distance ASC, c2.date DESC
                LIMIT 20
                """
                
                result = session.run(query, case_id=case_id)
                return [dict(record) for record in result]
        
        except Exception as e:
            logger.error(f"Failed to query precedents: {e}")
            return []
    
    def query_appellate_chain(
        self,
        case_id: str
    ) -> List[Dict[str, Any]]:
        """
        Query full appellate chain for a case.
        
        Traverses APPEALS_FROM relationships with confidence filtering.
        Returns edge metadata (confidence, reversal_status, extraction_method).
        
        Args:
            case_id: Case to find appellate chain for
        
        Returns:
            List of cases in appellate chain (bottom to top) with edge metadata
        """
        try:
            if self.APPEALS_FROM_REL not in self._get_relationship_types():
                logger.debug(f"Skipping appellate traversal: relationship type '{self.APPEALS_FROM_REL}' not present")
                return []

            with self.driver.session() as session:
                query = f"""
                MATCH path = (lower:{self.CASE_LABEL})-[r:{self.APPEALS_FROM_REL}*0..3]->(upper:{self.CASE_LABEL} {{case_id: $case_id}})
                WITH lower, path, relationships(path) as rels,
                     CASE WHEN size(relationships(path)) > 0 THEN properties(last(relationships(path))) ELSE {{}} END as last_rel_props
                RETURN lower.citation as citation, lower.case_id as case_id, lower.court as court, 
                       lower.date as date,
                       CASE WHEN size(rels) > 0 THEN coalesce(last_rel_props['reversal_status'], 'CURRENT') ELSE 'CURRENT' END as reversal_status,
                       CASE WHEN size(rels) > 0 THEN coalesce(last_rel_props['confidence'], 1.0) ELSE 1.0 END as confidence,
                       CASE WHEN size(rels) > 0 THEN coalesce(last_rel_props['extraction_method'], 'primary_record') ELSE 'primary_record' END as extraction_method,
                       length(path) as distance
                ORDER BY distance ASC
                """
                
                result = session.run(query, case_id=case_id)
                return [dict(record) for record in result]
        
        except Exception as e:
            logger.error(f"Failed to query appellate chain: {e}")
            return []
    
    def query_cases_by_statute(
        self,
        statute_name: str,
        section: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find all cases that interpret a specific statute/section.
        
        Args:
            statute_name: Name of statute to search for
            section: Specific section (optional)
            limit: Maximum results
        
        Returns:
            List of matching cases
        """
        try:
            with self.driver.session() as session:
                query = f"""
                MATCH (c:{self.CASE_LABEL})-[:{self.INTERPRETS_REL}]->(s:{self.STATUTE_LABEL})
                WHERE s.statute_name = $statute_name
                {'AND s.section = $section' if section else ''}
                RETURN c.citation as citation, c.date as date, c.court as court,
                       c.decision as decision, s.interpretation_summary as interpretation
                ORDER BY c.date DESC
                LIMIT {limit}
                """
                
                result = session.run(query, statute_name=statute_name, section=section)
                return [dict(record) for record in result]
        
        except Exception as e:
            logger.error(f"Failed to query cases by statute: {e}")
            return []
    
    @staticmethod
    def _normalize_citation(citation: str) -> str:
        """
        Normalize case citation for index-based lookups.
        
        Removes extra spaces, standardizes common patterns.
        
        Args:
            citation: Raw citation string
        
        Returns:
            Normalized citation
        """
        if not citation:
            return ""
        # Remove extra whitespace and convert to lowercase for matching
        return " ".join(citation.split()).lower()
    
    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed")
