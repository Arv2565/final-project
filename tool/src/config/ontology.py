"""
Legal Domain Ontology for Triple Extraction

Defines the structured vocabulary of entity types and relationship types
for extracting meaningful legal knowledge from Indian legal documents.
This ontology guides the LLM toward domain-specific extractions.
"""

from enum import Enum
from typing import Dict, List, Set, Tuple


class EntityType(str, Enum):
    """Legal entity types recognized in the Indian legal domain."""
    
    # Legislative/Statutory Entities
    LEGAL_ACT = "Legal_Act"  # e.g., Indian Penal Code, CPC, CRPC
    STATUTE = "Statute"  # General statutory law
    CONSTITUTION = "Constitution"  # Constitutional document
    SECTION = "Section"  # Section/Part/Article/Rule number
    CHAPTER = "Chapter"  # Chapter grouping inside an Act
    ARTICLE = "Article"  # Article (Constitutional style) or equivalent
    CLAUSE = "Clause"  # Specific clause within section
    SUBSECTION = "Subsection"  # Subsection inside a Section
    SCHEDULE = "Schedule"  # Schedule to an act
    
    # Substantive Legal Concepts
    DEFINITION = "Definition"  # Defined terms (e.g., "Grievous Hurt", "Competency")
    OFFENCE = "Offence"  # Criminal offences/crimes
    PENALTY = "Penalty"  # Punishments/penalties/imprisonment terms
    RIGHT = "Right"  # Legal rights/freedoms/entitlements
    DUTY = "Duty"  # Legal obligations/duties
    LIABILITY = "Liability"  # Legal liability
    EXEMPTION = "Exemption"  # Exemptions/exceptions to rules
    PROCEDURE = "Procedure"  # Legal procedures/processes
    
    # Institutional/Authority Entities
    COURT = "Court"  # Court entities (Supreme Court, High Court, District Court, etc.)
    TRIBUNAL = "Tribunal"  # Tribunals and specialized courts
    AUTHORITY = "Authority"  # Administrative/regulatory authorities
    OFFICER = "Officer"  # Judicial/administrative officers
    
    # Role/Party Entities
    PERSON_ROLE = "Person_Role"  # Legal roles (Judge, Defendant, Appellant, etc.)
    PARTY = "Party"  # Parties to legal proceedings
    
    # Jurisdictional Entities
    JURISDICTION = "Jurisdiction"  # Jurisdictional areas
    TERRITORY = "Territory"  # Geographic territories
    
    # Temporal Entities
    TIMEFRAME = "Timeframe"  # Specific time periods, deadlines
    EFFECTIVE_DATE = "Effective_Date"  # Effective dates of provisions
    
    # Evidence/Fact Entities
    EVIDENCE_TYPE = "Evidence_Type"  # Types of evidence
    FACT_PATTERN = "Fact_Pattern"  # Common fact patterns
    
    # General
    OTHER = "Other"  # Unclassified legal entities
    
    # New Entities for BNS/BNSS/BSA
    ILLUSTRATION = "Illustration"  # Hypothetical example clarifying a section
    EXPLANATION = "Explanation"  # Statutory explanation attached to a section


class RelationType(str, Enum):
    """Legal relationship types recognized in the Indian legal domain."""
    
    # Definitional and Conceptual Relations
    DEFINES = "defines"  # X defines Y
    DEFINED_IN = "defined_in"  # Y is defined in X
    IS_INSTANCE_OF = "is_instance_of"  # Y is an instance/example of X
    CLASSIFIES = "classifies"  # X classifies Y into categories
    
    # Structural Relations
    PART_OF = "part_of"  # Y is part of X (e.g., Section 2 is part of IPC)
    CONTAINS = "contains"  # X contains Y
    CHAPTER_IN = "chapter_in"  # X is a chapter in Y
    SECTION_IN = "section_in"  # X is a section in Y
    SUBSECTION_OF = "subsection_of"  # X is a subsection of Y
    BELONGS_TO = "belongs_to"  # Generic parent/child relationship for hierarchy
    
    # Establishment/Authority Relations
    ESTABLISHES = "establishes"  # X establishes Y (rule, right, court, etc.)
    ESTABLISHED_BY = "established_by"  # Y is established by X
    GOVERNS = "governs"  # X governs Y
    GOVERNED_BY = "governed_by"  # Y is governed by X
    CREATES = "creates"  # X creates Y (obligation, right, etc.)
    
    # Specification/Requirement Relations
    SPECIFIES = "specifies"  # X specifies procedure/conditions for Y
    SPECIFIED_IN = "specified_in"  # Y is specified in X
    REQUIRES = "requires"  # X requires Y to be satisfied
    REQUIRED_BY = "required_by"  # Y is required by X
    MANDATES = "mandates"  # X mandates Y
    MANDATED_BY = "mandated_by"  # Y is mandated by X
    PROVIDES = "provides"  # X provides mechanism/procedure for Y
    PROVIDED_BY = "provided_by"  # Y is provided by X
    
    # Amendment and Modification Relations
    AMENDS = "amends"  # X amends Y
    AMENDED_BY = "amended_by"  # Y is amended by X
    REPLACES = "replaces"  # X replaces/supersedes Y
    REPLACED_BY = "replaced_by"  # Y is replaced by X
    REPEALS = "repeals"  # X repeals Y
    REPEALED_BY = "repealed_by"  # Y is repealed by X
    MODIFIES = "modifies"  # X modifies Y
    MODIFIED_BY = "modified_by"  # Y is modified by X
    
    # Legal Force Relations
    OVERRULES = "overrules"  # X overrules Y (higher authority)
    OVERRULED_BY = "overruled_by"  # Y is overruled by X
    SUPERSEDES = "supersedes"  # X supersedes Y (takes precedence)
    SUPERSEDED_BY = "superseded_by"  # Y is superseded by X
    CONTRADICTS = "contradicts"  # X contradicts Y
    CONTRADICTED_BY = "contradicted_by"  # Y is contradicted by X
    CONSISTENT_WITH = "consistent_with"  # X is consistent with Y
    RECONCILES = "reconciles"  # X reconciles conflict between Y and Z
    
    # Application/Applicability Relations
    APPLIES_TO = "applies_to"  # X applies to Y (scope)
    APPLIED_BY = "applied_by"  # Y is applied by X
    APPLICABLE_TO = "applicable_to"  # X is applicable to Y
    EXCLUDES = "excludes"  # X excludes Y (exempts from scope)
    EXCLUDED_FROM = "excluded_from"  # Y is excluded from X
    EXEMPTS = "exempts"  # X exempts Y
    EXEMPTED_BY = "exempted_by"  # Y is exempted by X
    
    # Enforcement and Implementation
    ENFORCED_BY = "enforced_by"  # X is enforced by Y (court, authority)
    ENFORCES = "enforces"  # Y enforces X
    IMPLEMENTED_BY = "implemented_by"  # X is implemented by Y
    IMPLEMENTS = "implements"  # Y implements X
    INTERPRETED_BY = "interpreted_by"  # X is interpreted by Y (court)
    INTERPRETS = "interprets"  # Y interprets X
    ADJUDICATED_BY = "adjudicated_by"  # X is adjudicated by Y (court)
    ADJUDICATES = "adjudicates"  # Y adjudicates X
    
    # Criminal/Penalty Relations
    PENALIZES = "penalizes"  # X penalizes Y (offence)
    PENALIZED_UNDER = "penalized_under"  # Y is penalized under X
    PUNISHES = "punishes"  # X punishes Y (specific punishment)
    PUNISHED_UNDER = "punished_under"  # Y is punished under X
    LIABLE_UNDER = "liable_under"  # Y is liable under X
    CREATES_LIABILITY = "creates_liability"  # X creates liability for Y
    
    # Procedural Relations
    PROCEDURE_FOR = "procedure_for"  # X is procedure for Y
    PROCEDURE_UNDER = "procedure_under"  # X is procedure under Y
    PREREQUISITE_TO = "prerequisite_to"  # X is prerequisite to Y
    PREREQUISITE_OF = "prerequisite_of"  # Y has prerequisite X
    PRECEDES = "precedes"  # X comes before Y (procedurally)
    PRECEDED_BY = "preceded_by"  # Y is preceded by X
    FOLLOWED_BY = "followed_by"  # X is followed by Y (procedure)
    
    # Jurisdictional Relations
    JURISDICTION_OF = "jurisdiction_of"  # X has jurisdiction of Y
    HAS_JURISDICTION = "has_jurisdiction"  # X has jurisdiction over Y
    WITHIN_JURISDICTION = "within_jurisdiction"  # X is within jurisdiction of Y
    TERRITORIAL_SCOPE = "territorial_scope"  # X applies to territory Y
    
    # Reference Relations (Citations)
    CITED_IN = "cited_in"  # X is cited in Y (document/case)
    CITES = "cites"  # Y cites X
    REFERENCED_IN = "referenced_in"  # X is referenced in Y
    REFERENCES = "references"  # Y references X
    REFERS_TO = "refers_to"  # X refers to Y
    REFERRED_TO_IN = "referred_to_in"  # X is referred to in Y
    RELIES_ON = "relies_on"  # X relies on Y
    RELIED_UPON_BY = "relied_upon_by"  # X is relied upon by Y
    
    # Derivation/Basis Relations
    DERIVED_FROM = "derived_from"  # X is derived from Y
    BASIS_FOR = "basis_for"  # X is basis for Y
    BASED_ON = "based_on"  # X is based on Y
    GROUNDS_FOR = "grounds_for"  # X provides grounds for Y
    GROUNDED_IN = "grounded_in"  # X is grounded in Y
    
    # Conflict Resolution Relations
    RESOLVES_CONFLICT = "resolves_conflict"  # X resolves conflict with Y
    CONFLICTS_WITH = "conflicts_with"  # X conflicts with Y
    HARMONIZES_WITH = "harmonizes_with"  # X harmonizes with Y
    
    # Explanatory Relations
    HAS_ILLUSTRATION = "has_illustration"  # X has illustration Y
    HAS_EXPLANATION = "has_explanation"  # X has explanation Y
    ILLUSTRATES = "illustrates"  # Y illustrates X
    EXPLAINS = "explains"  # Y explains X
    
    # Relationship Relations
    RELATED_TO = "related_to"  # X is related to Y (generic/weak relation)
    RELATED = "related"  # X is related to Y (variant)
    COMPLEMENTS = "complements"  # X complements Y
    SUPPORTED_BY = "supported_by"  # X is supported by Y
    SUPPORTS = "supports"  # Y supports X
    
    # Other
    OTHER = "other"  # Unclassified relationship


class LegalOntology:
    """Central registry for legal ontology with validation and utilities."""
    
    # Valid entity types
    ENTITY_TYPES: Set[str] = {e.value for e in EntityType}
    
    # Valid relation types
    RELATION_TYPES: Set[str] = {r.value for r in RelationType}
    
    # Mapping of common LLM outputs to canonical relation types
    RELATION_ALIASES: Dict[str, str] = {
        # Amendments
        "amend": "amends",
        "amended": "amended_by",
        "amends": "amends",
        "amendment of": "amends",
        "amendment": "amends",
        
        # Citations
        "cite": "cites",
        "cited": "cited_in",
        "cites": "cites",
        "citation": "cites",
        "cited in": "cited_in",
        
        # References
        "refer": "references",
        "referred": "referred_to_in",
        "refers": "references",
        "reference": "references",
        "referenced": "referenced_in",
        "referenced in": "referenced_in",
        
        # Jurisdiction
        "judge": "adjudicates",
        "judged": "adjudicated_by",
        "judged by": "adjudicated_by",
        "court decides": "adjudicates",
        
        # Enforcement
        "enforce": "enforces",
        "enforced": "enforced_by",
        "enforced by": "enforced_by",
        "enforcement": "enforces",
        
        # Relationship
        "relate": "related_to",
        "related": "related_to",
        "relates": "related_to",
        "related to": "related_to",
        
        # Defines
        "define": "defines",
        "defines": "defines",
        "definition": "defines",
        
        # Parts
        "part": "part_of",
        "part of": "part_of",
        "section": "section_in",
        "article": "section_in",
        
        # Procedures
        "procedure": "procedure_for",
        "procedure for": "procedure_for",
        # Procedures
        "procedure": "procedure_for",
        "procedure for": "procedure_for",
        "procedural": "procedure_for",
        
        # Illustrations/Explanations
        "illustration": "has_illustration",
        "example": "has_illustration",
        "explanation": "has_explanation",
        "explains": "explains",
        "illustrates": "illustrates",
        
        # Penalties
        "penalize": "penalizes",
        "punish": "punishes",
        "penalty": "penalizes",
        "punishment": "punishes",
        
        # Jurisdictional
        "jurisdiction": "has_jurisdiction",
        "jurisdictional": "has_jurisdiction",
    }
    
    # Mapping of canonical relation types to Neo4j relationship type labels
    # Converts lowercase canonical types (e.g., "amends") to uppercase Neo4j types (e.g., "AMENDS")
    RELATION_TO_CYPHER_TYPE: Dict[str, str] = {
        # Definitional and Conceptual Relations
        "defines": "DEFINES",
        "defined_in": "DEFINED_IN",
        "is_instance_of": "IS_INSTANCE_OF",
        "classifies": "CLASSIFIES",
        
        # Structural Relations
        "part_of": "PART_OF",
        "contains": "CONTAINS",
        "chapter_in": "CHAPTER_IN",
        "section_in": "SECTION_IN",
        "subsection_of": "SUBSECTION_OF",
        "belongs_to": "BELONGS_TO",
        
        # Establishment/Authority Relations
        "establishes": "ESTABLISHES",
        "established_by": "ESTABLISHED_BY",
        "governs": "GOVERNS",
        "governed_by": "GOVERNED_BY",
        "creates": "CREATES",
        
        # Specification/Requirement Relations
        "specifies": "SPECIFIES",
        "specified_in": "SPECIFIED_IN",
        "requires": "REQUIRES",
        "required_by": "REQUIRED_BY",
        "mandates": "MANDATES",
        "mandated_by": "MANDATED_BY",
        "provides": "PROVIDES",
        "provided_by": "PROVIDED_BY",
        
        # Amendment and Modification Relations
        "amends": "AMENDS",
        "amended_by": "AMENDED_BY",
        "replaces": "REPLACES",
        "replaced_by": "REPLACED_BY",
        "repeals": "REPEALS",
        "repealed_by": "REPEALED_BY",
        "modifies": "MODIFIES",
        "modified_by": "MODIFIED_BY",
        
        # Legal Force Relations
        "overrules": "OVERRULES",
        "overruled_by": "OVERRULED_BY",
        "supersedes": "SUPERSEDES",
        "superseded_by": "SUPERSEDED_BY",
        "contradicts": "CONTRADICTS",
        "contradicted_by": "CONTRADICTED_BY",
        "consistent_with": "CONSISTENT_WITH",
        "reconciles": "RECONCILES",
        
        # Application/Applicability Relations
        "applies_to": "APPLIES_TO",
        "applied_by": "APPLIED_BY",
        "applicable_to": "APPLICABLE_TO",
        "excludes": "EXCLUDES",
        "excluded_from": "EXCLUDED_FROM",
        "exempts": "EXEMPTS",
        "exempted_by": "EXEMPTED_BY",
        
        # Enforcement and Implementation
        "enforced_by": "ENFORCED_BY",
        "enforces": "ENFORCES",
        "implemented_by": "IMPLEMENTED_BY",
        "implements": "IMPLEMENTS",
        "interpreted_by": "INTERPRETED_BY",
        "interprets": "INTERPRETS",
        "adjudicated_by": "ADJUDICATED_BY",
        "adjudicates": "ADJUDICATES",
        
        # Criminal/Penalty Relations
        "penalizes": "PENALIZES",
        "penalized_under": "PENALIZED_UNDER",
        "punishes": "PUNISHES",
        "punished_under": "PUNISHED_UNDER",
        "liable_under": "LIABLE_UNDER",
        "creates_liability": "CREATES_LIABILITY",
        
        # Procedural Relations
        "procedure_for": "PROCEDURE_FOR",
        "procedure_under": "PROCEDURE_UNDER",
        "prerequisite_to": "PREREQUISITE_TO",
        "prerequisite_of": "PREREQUISITE_OF",
        "precedes": "PRECEDES",
        "preceded_by": "PRECEDED_BY",
        "followed_by": "FOLLOWED_BY",
        
        # Jurisdictional Relations
        "jurisdiction_of": "JURISDICTION_OF",
        "has_jurisdiction": "HAS_JURISDICTION",
        "within_jurisdiction": "WITHIN_JURISDICTION",
        "territorial_scope": "TERRITORIAL_SCOPE",
        
        # Reference Relations (Citations)
        "cited_in": "CITED_IN",
        "cites": "CITES",
        "referenced_in": "REFERENCED_IN",
        "references": "REFERENCES",
        "refers_to": "REFERS_TO",
        "referred_to_in": "REFERRED_TO_IN",
        "relies_on": "RELIES_ON",
        "relied_upon_by": "RELIED_UPON_BY",
        
        # Derivation/Basis Relations
        "derived_from": "DERIVED_FROM",
        "basis_for": "BASIS_FOR",
        "based_on": "BASED_ON",
        "grounds_for": "GROUNDS_FOR",
        "grounded_in": "GROUNDED_IN",
        
        # Conflict Resolution Relations
        # Conflict Resolution Relations
        "resolves_conflict": "RESOLVES_CONFLICT",
        "conflicts_with": "CONFLICTS_WITH",
        "harmonizes_with": "HARMONIZES_WITH",
        
        # Explanatory Relations
        "has_illustration": "HAS_ILLUSTRATION",
        "has_explanation": "HAS_EXPLANATION",
        "illustrates": "ILLUSTRATES",
        "explains": "EXPLAINS",
        
        # Relationship Relations
        "related_to": "RELATED_TO",
        "related": "RELATED",
        "complements": "COMPLEMENTS",
        "supported_by": "SUPPORTED_BY",
        "supports": "SUPPORTS",
        
        # Other
        "other": "OTHER",
    }
    
    @classmethod
    def is_valid_entity_type(cls, entity_type: str) -> bool:
        """Check if entity type is valid."""
        return entity_type in cls.ENTITY_TYPES
    
    @classmethod
    def is_valid_relation_type(cls, relation_type: str) -> bool:
        """Check if relation type is valid."""
        return relation_type in cls.RELATION_TYPES
    
    @classmethod
    def add_relation_type(cls, relation: str) -> str:
        """Dynamically register a new canonical relation type at runtime.

        This updates the in-memory ontology so that subsequent triples in the
        same process can treat the new relation as first-class.

        Args:
            relation: Proposed canonical relation label (e.g., "triggers_review").

        Returns:
            The normalized (lowercase) relation label that was registered.
        """
        rel = relation.lower().strip()
        if not rel:
            raise ValueError("relation must be non-empty")

        if rel not in cls.RELATION_TYPES:
            cls.RELATION_TYPES.add(rel)

        if rel not in cls.RELATION_TO_CYPHER_TYPE:
            cls.RELATION_TO_CYPHER_TYPE[rel] = rel.upper()

        return rel
    
    @classmethod
    def relation_to_cypher_type(cls, relation: str) -> str:
        """
        Convert canonical relation type to Neo4j relationship type label.
        
        Args:
            relation: Canonical relation type (e.g., 'amends', 'cites', 'part_of')
            
        Returns:
            Neo4j relationship type label (e.g., 'AMENDS', 'CITES', 'PART_OF')
            Returns 'RELATION' as fallback if not found in mapping
        """
        relation_lower = relation.lower().strip()
        return cls.RELATION_TO_CYPHER_TYPE.get(relation_lower, "RELATION")
    
    @classmethod
    def get_cypher_type_for_relations(cls, relations: List[str]) -> List[str]:
        """
        Convert a list of canonical relations to Neo4j type labels.
        
        Args:
            relations: List of canonical relation types
            
        Returns:
            List of Neo4j relationship type labels
        """
        return [cls.relation_to_cypher_type(rel) for rel in relations]
    
    @classmethod
    def normalize_relation(cls, relation: str) -> Tuple[str, float]:
        """
        Normalize relation to canonical form with confidence score.
        
        Returns:
            (canonical_relation, confidence_score)
            - confidence = 1.0 if exact match
            - confidence = 0.8 if normalized via alias
            - confidence = 0.5 if no match (returned as-is with low confidence)
        """
        relation_lower = relation.lower().strip()
        
        # Exact match
        if relation_lower in cls.RELATION_TYPES:
            return (relation_lower, 1.0)
        
        # Alias match
        if relation_lower in cls.RELATION_ALIASES:
            canonical = cls.RELATION_ALIASES[relation_lower]
            return (canonical, 0.8)
        
        # No match - return original with low confidence
        return (relation, 0.5)
    
    @classmethod
    def get_entity_description(cls, entity_type: str) -> str:
        """Get description of an entity type."""
        descriptions = {
            EntityType.LEGAL_ACT.value: "Legislative act or statute (e.g., Indian Penal Code)",
            EntityType.STATUTE.value: "General statutory law",
            EntityType.CONSTITUTION.value: "Constitutional document",
            EntityType.SECTION.value: "Section, Part, Article, or Rule number",
            EntityType.CLAUSE.value: "Specific clause within a section",
            EntityType.DEFINITION.value: "Defined legal term",
            EntityType.OFFENCE.value: "Criminal offence or crime",
            EntityType.PENALTY.value: "Punishment or penalty",
            EntityType.RIGHT.value: "Legal right or entitlement",
            EntityType.DUTY.value: "Legal obligation or duty",
            EntityType.PROCEDURE.value: "Legal procedure or process",
            EntityType.COURT.value: "Court institution",
            EntityType.AUTHORITY.value: "Administrative or regulatory authority",
            EntityType.AUTHORITY.value: "Administrative or regulatory authority",
            EntityType.JURISDICTION.value: "Jurisdictional area",
            EntityType.ILLUSTRATION.value: "Hypothetical example clarifying a section",
            EntityType.EXPLANATION.value: "Statutory explanation attached to a section",
        }
        return descriptions.get(entity_type, "Legal entity")

    @classmethod
    def validate_canonical_id(cls, canonical_id: str, entity_type: str) -> Tuple[bool, str]:
        """Validate canonical ID format for entity type.
        
        Args:
            canonical_id: Canonical ID to validate (e.g., "IPC:Section:420")
            entity_type: Entity type to validate against
            
        Returns:
            (is_valid, error_message)
        """
        if not canonical_id:
            return False, f"Canonical ID must be provided: {canonical_id}"
        
        parts = canonical_id.split(":")
        
        # Statute/Act IDs: allow either 'IPC' or 'IPC:1860'
        if entity_type == EntityType.LEGAL_ACT.value or entity_type == EntityType.STATUTE.value:
            # Accept single-part abbreviations (e.g., 'IPC') or 'IPC:1860'
            # Reject obvious section-style identifiers when validating a statute id
            if parts and parts[0].lower() == 'section':
                return False, f"Statute ID must be 'ABB' or 'ABB:YEAR': {canonical_id}"

            if len(parts) == 1:
                return True, ""
            if len(parts) == 2:
                try:
                    int(parts[1])  # Year must be numeric
                except ValueError:
                    return False, f"Statute year must be numeric: {canonical_id}"
                return True, ""
            return False, f"Statute ID must be 'ABB' or 'ABB:YEAR': {canonical_id}"
        
        # Section IDs: "IPC:Section:420" or "IPC:Section:420(1)" or "IPC:Section:420(1)(a)"
        if entity_type == EntityType.SECTION.value:
            if len(parts) < 3:
                return False, f"Section ID must be 'STATUTE:Section:NUMBER': {canonical_id}"
            if parts[1] != "Section":
                return False, f"Section ID must have 'Section' in position 1: {canonical_id}"
            # parts[2] is the section number, may have subsections/clauses
            return True, ""
        
        # Chapter IDs: "IPC:Chapter:17" or "IPC:Chapter:XVII"
        if entity_type == EntityType.CHAPTER.value or entity_type == EntityType.ARTICLE.value:
            if len(parts) < 3:
                return False, f"Chapter ID must be 'STATUTE:Chapter:NUMBER': {canonical_id}"
            if not (parts[1] == "Chapter" or parts[1] == "Article"):
                return False, f"Chapter ID must have 'Chapter' or 'Article' in position 1: {canonical_id}"
            return True, ""
        
        # Case IDs: "AIR_1970_SC_1876" or similar reporter format
        if "Case" in entity_type or "_" in canonical_id:
            # Case citations use underscores: Reporter_Year_Court_Page
            parts = canonical_id.split("_")
            if len(parts) < 3:
                return False, f"Case ID must be 'REPORTER_YEAR_COURT_PAGE': {canonical_id}"
            try:
                int(parts[1])  # Year must be numeric
            except (ValueError, IndexError):
                return False, f"Case ID year must be numeric: {canonical_id}"
            return True, ""
        
        # Default: just check has some structure
        return len(parts) >= 2, f"Canonical ID should have multiple parts: {canonical_id}"
