"""
GraphRAG Indexer

- Flattens JSON into human-readable text blocks
- Chunks text
- Uses OpenAI chat model to extract (head, relation, tail) triples
- Validates triples with Pydantic
- Ingests nodes/edges into Neo4j
- Optionally embeds entities with text-embedding-3-large and creates a vector index
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional, Set, Tuple

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pydantic import BaseModel, Field, ValidationError, field_validator
from openai import OpenAI
from neo4j import Session

from src.config import get_settings, LegalOntology, EntityType, RelationType, get_embedding_config
from src.database.neo4j.client import neo4j_session
from .enrichment import normalize_name, canonicalize_entities_legal, enrich_relation, detect_doc_level_from_source, get_resolver
from .validation import flag_uncertain_triples
from src.utils.pdf import PDFTextExtractor


# Use centralized embedding config
embedding_config = get_embedding_config()
EMBED_MODEL = embedding_config.entity_embedding_model  # text-embedding-3-large by default
EMBED_DIM = embedding_config.entity_embedding_dimension  # 3072 by default

# OpenAI pricing rates (USD per 1K tokens) - from environment or defaults
DEFAULT_CHAT_INPUT_PER_1K = float(os.getenv("OPENAI_RATE_CHAT_INPUT_PER_1K", "5.00"))
DEFAULT_CHAT_OUTPUT_PER_1K = float(os.getenv("OPENAI_RATE_CHAT_OUTPUT_PER_1K", "15.00"))
DEFAULT_EMBED_PER_1K = float(os.getenv("OPENAI_RATE_EMBED_PER_1K", "0.13"))

logger = logging.getLogger(__name__)


class Triple(BaseModel):
    """Enhanced triple model with optional domain semantic and temporal fields."""
    
    head: str = Field(..., description="Subject entity")
    relation: str = Field(..., description="Relationship type")
    tail: str = Field(..., description="Object entity")
    
    # Optional domain-specific fields
    head_type: str = Field(default=EntityType.OTHER.value, description="Entity type of head (from EntityType enum)")
    tail_type: str = Field(default=EntityType.OTHER.value, description="Entity type of tail (from EntityType enum)")
    relation_confidence: float = Field(default=1.0, description="Confidence score of relation (0.5-1.0)")
    head_canonical_id: Optional[str] = Field(default=None, description="Optional canonical identifier for head (e.g., IPC:Section:420)")
    tail_canonical_id: Optional[str] = Field(default=None, description="Optional canonical identifier for tail (e.g., IPC:Chapter:XVII)")
    
    # Optional temporal validity fields for the relation
    effective_from: Optional[str] = Field(
        default=None,
        description="Optional ISO date (YYYY-MM-DD) when this relation becomes effective",
    )
    effective_to: Optional[str] = Field(
        default=None,
        description="Optional ISO date (YYYY-MM-DD) when this relation ceases to be effective",
    )
    
    @field_validator("head", "tail")
    @classmethod
    def validate_non_empty(cls, v):
        """Ensure head/tail are non-empty strings."""
        if not v or not str(v).strip():
            raise ValueError("head and tail must be non-empty")
        return str(v).strip()
    
    @field_validator("relation")
    @classmethod
    def validate_relation_not_empty(cls, v):
        """Ensure relation is non-empty."""
        if not v or not str(v).strip():
            raise ValueError("relation must be non-empty")
        return str(v).strip()
    
    @field_validator("effective_from", "effective_to")
    @classmethod
    def validate_effective_dates(cls, v):
        """Normalize blank temporal fields to None and strip whitespace.
        
        We intentionally keep values as strings (expected ISO dates) so they can be
        stored directly in Neo4j as properties; downstream code can parse/compare
        as needed.
        """
        if v is None:
            return None
        v_str = str(v).strip()
        return v_str or None
    
    def normalize_and_validate(self) -> "Triple":
        """Normalize relation to canonical form and validate against legal ontology.
        
        Returns updated Triple with canonical relation and confidence score.
        """
        # Normalize relation to canonical form
        canonical_rel, confidence = LegalOntology.normalize_relation(self.relation)
        self.relation = canonical_rel
        self.relation_confidence = confidence
        
        # Validate entity types if provided
        if self.head_type and not LegalOntology.is_valid_entity_type(self.head_type):
            logger.warning(f"Invalid head_type '{self.head_type}', setting to OTHER")
            self.head_type = EntityType.OTHER.value
        
        if self.tail_type and not LegalOntology.is_valid_entity_type(self.tail_type):
            logger.warning(f"Invalid tail_type '{self.tail_type}', setting to OTHER")
            self.tail_type = EntityType.OTHER.value
        
        return self
    
    def to_dict_with_ontology(self) -> Dict[str, Any]:
        """Return triple as dict with all ontology + temporal fields."""
        return {
            "head": self.head,
            "head_type": self.head_type,
            "relation": self.relation,
            "relation_confidence": self.relation_confidence,
            "tail": self.tail,
            "tail_type": self.tail_type,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
        }


@dataclass
class IndexStats:
    files_processed: int = 0
    chunks_processed: int = 0
    triples_extracted: int = 0
    nodes_embedded: int = 0


@dataclass
class CostStats:
    chat_prompt_tokens: int = 0
    chat_completion_tokens: int = 0
    embed_tokens: int = 0

    def total_cost_usd(self) -> float:
        return (
            (self.chat_prompt_tokens / 1000.0) * DEFAULT_CHAT_INPUT_PER_1K
            + (self.chat_completion_tokens / 1000.0) * DEFAULT_CHAT_OUTPUT_PER_1K
            + (self.embed_tokens / 1000.0) * DEFAULT_EMBED_PER_1K
        )


def flatten_json(obj: Any, prefix: str = "") -> List[str]:
    lines: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            lines.extend(flatten_json(v, key))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            key = f"{prefix}[{i}]" if prefix else f"[{i}]"
            lines.extend(flatten_json(item, key))
    else:
        # Primitive
        value = str(obj)
        lines.append(f"{prefix}: {value}")
    return lines


def chunk_text(text: str, words_per_chunk: int, overlap_words: int) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    n = len(words)
    while i < n:
        chunk_words = words[i : i + words_per_chunk]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if i + words_per_chunk >= n:
            break
        i += max(1, words_per_chunk - overlap_words)
    return chunks


class GraphRAGIndexer:
    def __init__(self, create_vector_index: bool = True, force_reembed: bool = False):
        self.settings = get_settings()
        self.client = OpenAI()
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.create_vector_index = create_vector_index
        # If True, always recompute embeddings even when an existing vector is present.
        # Default False to enable deduplication across runs.
        self.force_reembed = force_reembed
        self.embed_dim = 3072
        self.pdf_extractor = PDFTextExtractor()
        self.cost = CostStats()

    def _extract_triples_llm(self, text: str, source: str = "") -> List[Triple]:
        """
        Extract legal triples from text using domain-aware LLM prompts.
        
        Args:
            text: Input text to extract triples from
            source: Source document name/path (used for context)
        
        Returns:
            List of validated Triple objects with ontology fields
        """
        # Determine document context (IPC, Constitution, CPC, etc.)
        doc_context = self._infer_doc_context(source)
        
        # Build domain-aware system prompt
        sys_prompt = f"""You are an expert legal knowledge extractor specializing in Indian legal documents.

Your task: Extract structured triples (head, relation, tail) from legal text, capturing meaningful legal relationships.

**Entity Types** you should assign:
- Legal_Act: Statutes like IPC, CPC, Constitution
- Section: Section/Part/Article/Rule numbers  
- Definition: Defined legal terms
- Offence: Criminal offences
- Penalty: Punishments or penalties
- Right: Legal rights or entitlements
- Duty: Legal obligations
- Court: Court institutions
- Procedure: Legal procedures
- Other: Anything not fitting above

**Relationship Types** you should use (NOT generic "relates_to"):
- defines / defined_in: Term definitions
- part_of / contains: Structural hierarchy
- establishes / established_by: Creates rules/rights/courts
- specifies / specified_in: Details procedures or conditions
- amends / amended_by / supersedes / repeals: Modification
- enforces / enforced_by / interprets / adjudicates: Application
- penalizes / punishes: Criminal penalties
- cited_in / cites / referenced_in: Legal citations
- procedure_for: Procedural relationships
- applies_to / excludes: Applicability scope
- Other valid relations: prerequisite_to, jurisdiction_of, grounded_in, etc.

**Output Format** (MUST be valid JSON array):
[
  {{
    "head": "entity name",
    "head_type": "entity type from list above",
    "relation": "canonical relationship type",
    "tail": "entity name",
    "tail_type": "entity type from list above",
    "effective_from": "YYYY-MM-DD or null (optional)",
    "effective_to": "YYYY-MM-DD or null (optional)"
  }},
  ...
]

**Rules**:
1. Return ONLY valid JSON array. No commentary, code fences, or extra text.
2. Each triple must have non-empty head, relation, and tail.
3. Use CANONICAL relationship types from the list. Avoid generic relations.
4. Assign entity_types based on the entity's role/nature.
5. Prioritize meaningful legal relationships over generic "related_to".
6. For procedural documents: extract procedure_for, prerequisite_to, precedes relationships.
7. For definitional sections: use defines, classifies, is_instance_of.
8. For amendment/repeal: use amends, supersedes, repeals (NOT just "amended").
9. If relation type unclear, omit the triple rather than using a wrong type.
10. Confidence in relationships matters—prioritize clear, explicit relationships over inferred ones.

Document Context: {doc_context}
"""

        # Few-shot examples from legal domain
        few_shot_examples = self._get_few_shot_examples()
        
        user_prompt = f"""Extract legal triples from this text. Use the entity types and relationship types specified in the system prompt.

    {few_shot_examples}

    **Text to extract from:**
    {text}

    Return a JSON array of triples where each triple has these fields: `head`, `head_type`, `relation`, `tail`, `tail_type`. Optionally include `head_canonical_id` and `tail_canonical_id` when a canonical identifier is evident (e.g., `IPC:Section:420`, `IPC:Chapter:XVII`). Prefer explicit hierarchical relations (e.g., `part_of`, `section_in`, `chapter_in`) for structural links. Return ONLY valid JSON, no other text."""

        resp = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        
        # Track token usage if available
        usage = getattr(resp, "usage", None)
        if usage is not None:
            try:
                prompt_tokens = getattr(usage, "prompt_tokens", None)
                if prompt_tokens is None and isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = getattr(usage, "completion_tokens", None)
                if completion_tokens is None and isinstance(usage, dict):
                    completion_tokens = usage.get("completion_tokens", 0)
                self.cost.chat_prompt_tokens += int(prompt_tokens or 0)
                self.cost.chat_completion_tokens += int(completion_tokens or 0)
            except Exception:
                pass
        
        content = resp.choices[0].message.content or "[]"
        
        # Strip code fences if any
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n|```$", "", content, flags=re.MULTILINE).strip()
        
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                data = []
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM JSON response: {content[:100]}")
            data = []
        
        triples: List[Triple] = []
        for item in data:
            try:
                t = Triple(**item)
                # Normalize and validate against ontology
                t = t.normalize_and_validate()

                # If ontology confidence is low (<= 0.5), try LLM-based repair / ontology extension
                if t.relation_confidence <= 0.5:
                    t = self._repair_relation_via_llm(t, text=text, source=source)

                # Basic sanitation: ensure all required fields are non-empty
                if t.head and t.relation and t.tail:
                    triples.append(t)
                else:
                    logger.debug(f"Skipped invalid triple after repair attempt: {item}")
            except ValidationError as e:
                logger.debug(f"Validation error for triple {item}: {e}")
                continue
        
        return triples
    
    def _repair_relation_via_llm(self, triple: Triple, text: str, source: str = "") -> Triple:
        """Attempt to repair low-confidence relations using the chat model.

        Behavior:
        - Only used when relation_confidence is already low (<= 0.5).
        - Asks the LLM to either map to an existing ontology relation or propose
          a new one.
        - If a new label is proposed, it is registered dynamically in
          LegalOntology so subsequent triples can use it.
        - On any failure or "none" response, the original triple is returned
          unchanged to avoid data loss.
        """
        # Defensive guard: only run for low-confidence relations
        if triple.relation_confidence > 0.5:
            return triple

        allowed = list(LegalOntology.RELATION_TYPES)

        sys_prompt = (
            "You are assisting with a legal ontology for Indian legal documents.\n"
            "Given a (head, relation, tail) triple and the source text, choose the BEST "
            "canonical relationship label.\n\n"
            "You have two options:\n"
            "1) Map to one of the EXISTING labels in this list.\n"
            "2) Propose a NEW label only if none of the existing labels are a good fit.\n\n"
            "Respond ONLY with a single JSON object like:\n"
            '{"relation": "<label>", "is_new": false}\n'
            "or, for a new label:\n"
            '{"relation": "<new_label>", "is_new": true}\n'
            "If no relation is appropriate at all, use:\n"
            '{"relation": "none", "is_new": false}'
        )

        user_prompt = (
            f"Existing relation labels: {allowed}\n\n"
            f"Head: {triple.head}\n"
            f"Original relation from model: {triple.relation}\n"
            f"Tail: {triple.tail}\n"
            f"Source: {source}\n\n"
            f"Relevant text span:\n{text}\n"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            content = (resp.choices[0].message.content or "").strip()
            # Strip code fences if any
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n|```$", "", content, flags=re.MULTILINE).strip()

            data = json.loads(content)
            new_rel = str(data.get("relation", "")).strip().lower()
            is_new = bool(data.get("is_new", False))
        except Exception as e:
            logger.warning(
                f"LLM relation repair failed for triple {triple.head} --[{triple.relation}]--> {triple.tail}: {e}"
            )
            return triple

        if not new_rel or new_rel == "none":
            logger.debug(
                f"LLM did not provide a better relation for {triple.head} --[{triple.relation}]--> {triple.tail}"
            )
            return triple

        # Case 1: mapped to an existing ontology relation
        if new_rel in LegalOntology.RELATION_TYPES:
            triple.relation = new_rel
            triple.relation_confidence = 0.9
            logger.info(
                f"Repaired relation using existing ontology: "
                f"{triple.head} --[{triple.relation}]--> {triple.tail}"
            )
            return triple

        # Case 2: LLM proposes a new relation; extend ontology at runtime
        try:
            canonical = LegalOntology.add_relation_type(new_rel)
            triple.relation = canonical
            triple.relation_confidence = 0.8
            logger.warning(
                f"Extended ontology with new relation '{canonical}' from LLM for "
                f"{triple.head} --[{canonical}]--> {triple.tail}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to extend ontology with relation '{new_rel}' for "
                f"{triple.head} --[{triple.relation}]--> {triple.tail}: {e}"
            )

        return triple
    
    def _infer_doc_context(self, source: str) -> str:
        """Infer document context from source path for prompt guidance."""
        source_lower = source.lower()
        
        if "constitution" in source_lower:
            return "This text is from the Constitution of India (foundational law, articles and schedules)"
        elif "ipc" in source_lower or "penal" in source_lower:
            return "This text is from the Indian Penal Code (criminal law, sections with offences and penalties)"
        elif "cpc" in source_lower or "civil" in source_lower:
            return "This text is from the Code of Civil Procedure (civil litigation procedures)"
        elif "crpc" in source_lower or "criminal" in source_lower:
            return "This text is from the Code of Criminal Procedure (criminal investigation/trial procedures)"
        elif "evidence" in source_lower or "iea" in source_lower:
            return "This text is from the Indian Evidence Act (rules for admissibility of evidence)"
        elif "marriage" in source_lower or "hma" in source_lower:
            return "This text is from the Hindu Marriage Act (marriage and divorce law)"
        elif "motor" in source_lower or "mva" in source_lower:
            return "This text is from the Motor Vehicle Act (traffic and vehicle regulations)"
        else:
            return "This text is from Indian legal documents"
    
    def _get_few_shot_examples(self) -> str:
        """Load and format few-shot examples from legal extraction examples."""
        try:
            examples_path = Path(__file__).parent.parent.parent / "config" / "legal_extraction_examples.json"
            if examples_path.exists():
                examples_data = json.loads(examples_path.read_text())
                examples = examples_data.get("examples", [])[:3]  # Use first 3 examples
                
                formatted_examples = "**Examples of correct extractions:**\n"
                for ex in examples:
                    formatted_examples += f"- From {ex.get('source', 'legal text')}: {ex.get('head', '')} --[{ex.get('relation', '')}]--> {ex.get('tail', '')}\n"
                return formatted_examples
        except Exception as e:
            logger.debug(f"Could not load few-shot examples: {e}")
        
        return "**Examples of correct extractions:**\n- Section 300 (Murder) --[defines]--> Intentional causing of death\n- IPC --[part_of]--> Indian Legal System\n- Court --[has_jurisdiction]--> Civil disputes\n"

    def _ensure_vector_index(self, session: Session) -> None:
        if not self.create_vector_index:
            return
        try:
            session.run(
                """
                CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS
                FOR (e:Entity) ON (e.embedding)
                OPTIONS { indexConfig: {`vector.dimensions`: $dims, `vector.similarity_function`: 'cosine'} }
                """,
                dims=self.embed_dim,
            )
        except Exception:
            # Older Neo4j versions may not support native vector index
            pass

    def _check_apoc_available(self, session: Session) -> bool:
        """Check if APOC is installed and available in Neo4j."""
        try:
            result = session.run("CALL apoc.version()")
            version = result.single()
            logger.info(f"APOC version: {version}")
            return True
        except Exception as e:
            logger.warning(f"APOC not available: {e}. Dynamic label assignment will be skipped. Install APOC plugin for full hierarchy support.")
            return False

    def _ingest_triples(self, triples: List[Triple], source: str, chunk_id: int, chunk_text: Optional[str] = None) -> Set[str]:
        """
        Insert nodes/edges with ontology-validated fields; return set of entity names touched.
        
        Stores entity types, relation confidence, and validates against ontology.
        """
        touched: Set[str] = set()
        if not triples:
            return touched
        
        # Normalize and canonicalize entities to reduce node proliferation
        original_names = [t.head.strip() for t in triples if t.head] + [t.tail.strip() for t in triples if t.tail]
        # Use legal canonicalization which uses the global resolver
        name_to_canon, canon_groups = canonicalize_entities_legal(original_names)

        # Global resolver (shared across ingestion) for per-entity canonical lookup
        resolver = get_resolver()

        law_level = detect_doc_level_from_source(source or "")

        with neo4j_session() as session:
            for t in triples:
                head_orig = t.head.strip()
                tail_orig = t.tail.strip()
                head = name_to_canon.get(head_orig, normalize_name(head_orig))
                tail = name_to_canon.get(tail_orig, normalize_name(tail_orig))
                enriched_rel = enrich_relation(t.relation.strip())
                
                # Flag low-confidence relations for review
                low_confidence = t.relation_confidence < 0.8
                if low_confidence:
                    logger.debug(f"Low-confidence triple (conf={t.relation_confidence:.2f}): {head_orig} --[{t.relation}]--> {tail_orig}")

                # Merge nodes using canonical names, but keep human-friendly display_name
                # Also store entity type for semantic understanding
                # Determine safe labels from ontology to set as explicit node labels
                head_label = t.head_type if t.head_type in LegalOntology.ENTITY_TYPES else None
                tail_label = t.tail_type if t.tail_type in LegalOntology.ENTITY_TYPES else None

                # Compute canonical ids using the resolver (preferred) and fall back to law_level prefix
                head_canon_id = resolver.get_canonical_id(head_orig, t.head_type) or (f"{law_level}:{head}" if head else None)
                tail_canon_id = resolver.get_canonical_id(tail_orig, t.tail_type) or (f"{law_level}:{tail}" if tail else None)

                # Temporal validity for this relation (optional, ISO strings)
                effective_from = t.effective_from
                effective_to = t.effective_to

                # Structural relations that imply parent-child hierarchy
                structural_rels = {RelationType.PART_OF.value, RelationType.SECTION_IN.value, RelationType.CHAPTER_IN.value, RelationType.SUBSECTION_OF.value, RelationType.CONTAINS.value, 'belongs_to'}

                # Get Neo4j typed relationship label from canonical relation
                cypher_rel_type = LegalOntology.relation_to_cypher_type(t.relation.strip())

                # Prepare a unique, file-scoped chunk node id (keep numeric chunk_id on relations for backward compatibility)
                chunk_node_id = f"{source}::chunk::{chunk_id}"

                # Step 1: Merge nodes with basic properties and create Chunk node linking
                # Use CALL to dynamically create typed relationships based on the canonical relation
                cypher_merge = f"""
                    MERGE (a:Entity {{name: $head}})
                    ON CREATE SET a.created_at = timestamp(), a.display_name = $head_orig
                    SET a.entity_type = $head_type, a.canonical_id = $head_canon_id, a.law_level = $law_level, a.source = $source
                    
                    MERGE (b:Entity {{name: $tail}})
                    ON CREATE SET b.created_at = timestamp(), b.display_name = $tail_orig
                    SET b.entity_type = $tail_type, b.canonical_id = $tail_canon_id, b.law_level = $law_level, b.source = $source

                    // create chunk node and link entities to chunk
                    MERGE (ch:Chunk {id: $chunk_node_id})
                    ON CREATE SET ch.created_at = timestamp(), ch.text = $chunk_text, ch.source = $source
                    MERGE (a)-[m:MENTIONED_IN]->(ch)
                    ON CREATE SET m.created_at = timestamp(), m.source = $source, m.chunk_id = $chunk_id
                    
                    CALL apoc.create.relationship(a, $rel_type, {{created_at: timestamp(), source: $source, chunk_id: $chunk_id, relation_tag: $enriched_rel, relation_confidence: $confidence, low_confidence: $low_confidence, valid_from: $effective_from, valid_until: $effective_to}}, b) YIELD rel
                    RETURN rel
                """

                try:
                    session.run(
                        cypher_merge,
                        head=head,
                        head_orig=head_orig,
                        head_type=t.head_type,
                        head_canon_id=head_canon_id,
                        tail=tail,
                        tail_orig=tail_orig,
                        tail_type=t.tail_type,
                        tail_canon_id=tail_canon_id,
                        rel_type=cypher_rel_type,
                        enriched_rel=enriched_rel,
                        chunk_node_id=chunk_node_id,
                        chunk_text=chunk_text,
                        source=source,
                        chunk_id=chunk_id,
                        law_level=law_level,
                        confidence=t.relation_confidence,
                        low_confidence=low_confidence,
                    )
                except Exception as e:
                    logger.warning(f"Failed to create typed relationship {cypher_rel_type} for {head} -> {tail}: {e}. Attempting fallback to generic RELATION.")
                    # Fallback to generic RELATION if APOC is unavailable
                    cypher_fallback = """
                        MERGE (a:Entity {name: $head})
                        ON CREATE SET a.created_at = timestamp(), a.display_name = $head_orig
                        SET a.entity_type = $head_type, a.canonical_id = $head_canon_id, a.law_level = $law_level, a.source = $source
                        
                        MERGE (b:Entity {name: $tail})
                        ON CREATE SET b.created_at = timestamp(), b.display_name = $tail_orig
                        SET b.entity_type = $tail_type, b.canonical_id = $tail_canon_id, b.law_level = $law_level, b.source = $source
                        
                        MERGE (a)-[r:RELATION {canonical_type: $canonical_rel}]->(b)
                        ON CREATE SET r.created_at = timestamp(), r.source = $source, r.chunk_id = $chunk_id
                        SET r.relation_tag = $enriched_rel, r.relation_confidence = $confidence, r.low_confidence = $low_confidence
                    """
                    session.run(
                        cypher_fallback,
                        head=head,
                        head_orig=head_orig,
                        head_type=t.head_type,
                        head_canon_id=head_canon_id,
                        tail=tail,
                        tail_orig=tail_orig,
                        tail_type=t.tail_type,
                        tail_canon_id=tail_canon_id,
                        canonical_rel=t.relation.strip(),
                        enriched_rel=enriched_rel,
                        chunk_node_id=chunk_node_id,
                        chunk_text=chunk_text,
                        source=source,
                        chunk_id=chunk_id,
                        law_level=law_level,
                        confidence=t.relation_confidence,
                        low_confidence=low_confidence,
                        effective_from=effective_from,
                        effective_to=effective_to,
                    )

                # Create a reverse relationship to enable efficient reverse lookups.
                try:
                    # Try to find an inverse canonical relation (e.g., 'amends' -> 'amended_by')
                    def _find_inverse(canonical_rel: str) -> Optional[str]:
                        # Common pattern: try '<rel>_by' or '<rel>_in' or past forms
                        if LegalOntology.is_valid_relation_type(canonical_rel + '_by'):
                            return canonical_rel + '_by'
                        if LegalOntology.is_valid_relation_type(canonical_rel + '_in'):
                            return canonical_rel + '_in'
                        if canonical_rel.endswith('s'):
                            alt = canonical_rel[:-1] + 'd_in'
                            if LegalOntology.is_valid_relation_type(alt):
                                return alt
                            alt2 = canonical_rel[:-1] + 'ed_by'
                            if LegalOntology.is_valid_relation_type(alt2):
                                return alt2
                        # Finally, scan known relation keys for a _by or _in variant
                        root = canonical_rel.split('_')[0]
                        for k in LegalOntology.RELATION_TO_CYPHER_TYPE.keys():
                            if k.startswith(root) and ('_by' in k or '_in' in k or 'ed' in k):
                                return k
                        return None

                    inv_canonical = _find_inverse(t.relation.strip())
                    if inv_canonical:
                        inv_type = LegalOntology.relation_to_cypher_type(inv_canonical)
                        # create inverse typed relationship b -> a
                        session.run(
                            """
                            MERGE (b:Entity {name: $tail})
                            MERGE (a:Entity {name: $head})
                            CALL apoc.create.relationship(b, $inv_type, {created_at: timestamp(), source: $source, chunk_id: $chunk_id, relation_confidence: $confidence, valid_from: $effective_from, valid_until: $effective_to}, a) YIELD rel
                            RETURN rel
                            """,
                            tail=tail,
                            head=head,
                            inv_type=inv_type,
                            source=source,
                            chunk_id=chunk_id,
                            confidence=t.relation_confidence,
                        )
                    else:
                        # Fallback: create reverse generic relation with reference to original
                        session.run(
                            """
                            MERGE (b:Entity {name: $tail})
                            MERGE (a:Entity {name: $head})
                            MERGE (b)-[r2:RELATION]->(a)
                            ON CREATE SET r2.created_at = timestamp(), r2.source = $source, r2.chunk_id = $chunk_id
                            SET r2.relation_tag = $enriched_rel, r2.relation_confidence = $confidence, r2.inverse_of = $canonical_rel
                            """,
                            tail=tail,
                            head=head,
                            source=source,
                            chunk_id=chunk_id,
                            enriched_rel=enriched_rel,
                            confidence=t.relation_confidence,
                            canonical_rel=t.relation.strip(),
                            effective_from=effective_from,
                            effective_to=effective_to,
                        )
                except Exception:
                    logger.debug("Failed to create reverse relationship; continuing")

                # Step 2: Dynamically add labels using APOC if entity_type is in ontology whitelist
                if head_label:
                    try:
                        session.run(
                            """
                            MATCH (a:Entity {name: $head})
                            CALL apoc.create.addLabels(a, [$label]) YIELD node
                            RETURN node
                            """,
                            head=head,
                            label=head_label,
                        )
                    except Exception as e:
                        logger.debug(f"APOC addLabels failed for head node {head_label}: {e}. Proceeding without dynamic label.")

                if tail_label:
                    try:
                        session.run(
                            """
                            MATCH (b:Entity {name: $tail})
                            CALL apoc.create.addLabels(b, [$label]) YIELD node
                            RETURN node
                            """,
                            tail=tail,
                            label=tail_label,
                        )
                    except Exception as e:
                        logger.debug(f"APOC addLabels failed for tail node {tail_label}: {e}. Proceeding without dynamic label.")

                # If the relation is structural, also create an explicit hierarchical relation
                try:
                    if t.relation.strip() in structural_rels:
                        # Use typed relationship instead of generic PART_OF_HIERARCHY
                        hierarchy_rel_type = LegalOntology.relation_to_cypher_type(t.relation.strip())
                        cypher_hierarchy = f"""
                            MERGE (a:Entity {{name: $head}})
                            MERGE (b:Entity {{name: $tail}})
                            CALL apoc.create.relationship(a, $hierarchy_rel_type, {{created_at: timestamp(), source: $source, chunk_id: $chunk_id, inferred: false, relation_confidence: $confidence, valid_from: $effective_from, valid_until: $effective_to}}, b) YIELD rel
                            RETURN rel
                        """
                        try:
                            session.run(
                                cypher_hierarchy,
                                head=head,
                                tail=tail,
                                hierarchy_rel_type=hierarchy_rel_type,
                                source=source,
                                chunk_id=chunk_id,
                                confidence=t.relation_confidence,
                            )
                        except Exception as e:
                            # Fallback to PART_OF_HIERARCHY if dynamic relationship creation fails
                            logger.debug(f"Failed to create typed hierarchy relationship {hierarchy_rel_type}: {e}. Using PART_OF_HIERARCHY fallback.")
                            session.run(
                                """
                                MERGE (a:Entity {name: $head})
                                MERGE (b:Entity {name: $tail})
                                MERGE (a)-[p:PART_OF_HIERARCHY]->(b)
                                ON CREATE SET p.created_at = timestamp(), p.source = $source, p.chunk_id = $chunk_id, p.inferred = false
                                SET p.relation_confidence = $confidence, p.valid_from = $effective_from, p.valid_until = $effective_to
                                """,
                                head=head,
                                tail=tail,
                                source=source,
                                chunk_id=chunk_id,
                                confidence=t.relation_confidence,
                                effective_from=effective_from,
                                effective_to=effective_to,
                            )
                except Exception:
                    # Non-critical if hierarchy relation creation fails
                    logger.debug("Failed to create explicit hierarchy relation; continuing")
                touched.add(head)
                touched.add(tail)
        
        return touched

    def _embed_entities(self, entity_names: Iterable[str]) -> int:
        names = list({n for n in entity_names if n})
        if not names:
            return 0
        # Compute embeddings in small batches
        total = 0
        with neo4j_session() as session:
            self._ensure_vector_index(session)
            # If not forcing re-embed, determine which entities already have embeddings
            names_to_embed = names
            if not self.force_reembed:
                try:
                    result = session.run(
                        """
                        UNWIND $names AS n
                        MATCH (e:Entity {name: n})
                        WHERE e.embedding IS NOT NULL
                        RETURN collect(DISTINCT n) AS already
                        """,
                        names=names,
                    )
                    record = result.single()
                    already = set(record.get("already", [])) if record else set()
                    names_to_embed = [n for n in names if n not in already]
                    if already:
                        logger.info(
                            f"Skipping embedding for {len(already)} entities that already have embeddings; "
                            f"embedding {len(names_to_embed)} new entities."
                        )
                except Exception as e:
                    logger.warning(f"Failed to check existing embeddings, embedding all entities: {e}")
                    names_to_embed = names
        if not names_to_embed:
            logger.info("No new entities to embed; skipping embedding step.")
            return 0
        batch_size = 128
        logger.info(f"Embedding {len(names_to_embed)} unique entities in batches of {batch_size}...")
        start = time.time()
        for i in range(0, len(names_to_embed), batch_size):
            batch = names_to_embed[i : i + batch_size]
            embeds = self.client.embeddings.create(model=EMBED_MODEL, input=batch)
            # Track embedding token usage if available
            emb_usage = getattr(embeds, "usage", None)
            if emb_usage is not None:
                try:
                    prompt_tokens = getattr(emb_usage, "prompt_tokens", None)
                    if prompt_tokens is None and isinstance(emb_usage, dict):
                        prompt_tokens = emb_usage.get("prompt_tokens", 0)
                    self.cost.embed_tokens += int(prompt_tokens or 0)
                except Exception:
                    pass
            vectors = [e.embedding for e in embeds.data]
            with neo4j_session() as session:
                for name, vec in zip(batch, vectors):
                    session.run(
                        """
                        MERGE (e:Entity {name: $name})
                        SET e.embedding = $embedding, e.last_embedded_at = timestamp()
                        """,
                        name=name,
                        embedding=vec,
                    )
                    total += 1
            done = min(i + batch_size, len(names))
            pct = (done / len(names)) * 100.0
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(names) - done) / rate if rate > 0 else float("inf")
            logger.info(
                f"Embedding progress: {done}/{len(names)} ({pct:.1f}%) | rate {rate:.1f}/s | ETA {eta:.1f}s | est cost ${self.cost.total_cost_usd():.2f}"
            )
        return total

    def index_json_files(
        self,
        paths: List[Path],
        recursive: bool = True,
        max_chunks_per_file: Optional[int] = None,
        embed_entities: bool = True,
    ) -> IndexStats:
        # Backward-compatible name, but now supports .json, .txt, .pdf
        stats = IndexStats()
        proc_cfg = self.settings.processing
        files: List[Path] = []
        exts = {".json", ".txt", ".pdf"}
        for p in paths:
            p = Path(p)
            if p.is_file() and p.suffix.lower() in exts:
                files.append(p)
            elif p.is_dir():
                if recursive:
                    for pat in ("*.json", "*.txt", "*.pdf"):
                        files.extend(list(p.rglob(pat)))
                else:
                    for pat in ("*.json", "*.txt", "*.pdf"):
                        files.extend(list(p.glob(pat)))
        if not files:
            logger.warning("No input files found for GraphRAG indexing.")
            return stats

        # Check APOC availability for dynamic labeling
        try:
            with neo4j_session() as session:
                apoc_available = self._check_apoc_available(session)
                if not apoc_available:
                    logger.warning("⚠️  APOC not installed. Dynamic entity labels will not be set. Install APOC for full hierarchy support: https://github.com/neo4j/apoc")
        except Exception as e:
            logger.warning(f"Could not check APOC availability: {e}")

        # Pre-scan to estimate total chunks for progress tracking
        prescan: List[Tuple[Path, List[str]]] = []
        total_chunks = 0
        logger.info(f"Pre-scanning {len(files)} files to estimate work...")
        for fp in files:
            try:
                text_blocks = self._prepare_text_blocks_from_path(fp)
                if not text_blocks:
                    prescan.append((fp, []))
                    continue
                chunks = chunk_text(
                    "\n".join(text_blocks),
                    words_per_chunk=proc_cfg.chunk_size,
                    overlap_words=proc_cfg.chunk_overlap,
                )
                if max_chunks_per_file is not None:
                    chunks = chunks[:max_chunks_per_file]
                prescan.append((fp, chunks))
                total_chunks += len(chunks)
            except Exception as e:
                logger.error(f"Pre-scan failed for {fp}: {e}")
                prescan.append((fp, []))

        logger.info(f"Discovered {len(files)} files, estimated {total_chunks} chunks to process.")

        seen_entities: Set[str] = set()
        processed_chunks = 0
        start_time = time.time()
        for file_idx, (fp, chunks) in enumerate(prescan, start=1):
            logger.info(f"[File {file_idx}/{len(files)}] {fp.name} | {len(chunks)} chunks")
            for idx, chunk in enumerate(chunks):
                try:
                    # Pass source context to extraction for better domain awareness
                    triples = self._extract_triples_llm(chunk, source=str(fp))
                    # Human-in-the-loop: flag uncertain triples for review (does not block ingestion)
                    try:
                        flag_uncertain_triples([t.to_dict_with_ontology() for t in triples])
                    except Exception:
                        logger.debug("Failed to write review queue; continuing")
                    touched = self._ingest_triples(triples, source=str(fp), chunk_id=idx, chunk_text=chunk)
                except Exception as e:
                    logger.error(f"Chunk {idx} failed for {fp.name}: {e}")
                    triples = []
                    touched = set()
                seen_entities.update(touched)
                stats.chunks_processed += 1
                stats.triples_extracted += len(triples)
                processed_chunks += 1

                pct = (processed_chunks / total_chunks) * 100.0 if total_chunks else 100.0
                elapsed = time.time() - start_time
                rate = processed_chunks / elapsed if elapsed > 0 else 0
                eta = (total_chunks - processed_chunks) / rate if rate > 0 else float("inf")
                logger.info(
                    f"Progress {processed_chunks}/{total_chunks} ({pct:.1f}%) | file {file_idx}/{len(files)} chunk {idx+1}/{len(chunks)} | triples +{len(triples)} (total {stats.triples_extracted}) | rate {rate:.2f} ch/s | ETA {eta:.1f}s | est cost ${self.cost.total_cost_usd():.2f}"
                )
            stats.files_processed += 1

        if embed_entities and seen_entities:
            stats.nodes_embedded = self._embed_entities(list(seen_entities))

        # Final summary
        logger.info(
            f"Completed indexing. Files: {stats.files_processed}, Chunks: {stats.chunks_processed}, Triples: {stats.triples_extracted}, Embedded nodes: {stats.nodes_embedded}, Estimated cost: ${self.cost.total_cost_usd():.2f}"
        )
        return stats

    def _prepare_text_blocks_from_path(self, path: Path) -> List[str]:
        suffix = path.suffix.lower()
        if suffix == ".json":
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            lines = flatten_json(data)
            text = "\n".join(lines)
        elif suffix == ".txt":
            try:
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = Path(path).read_text(errors="ignore")
        elif suffix == ".pdf":
            extracted = self.pdf_extractor.extract_text_from_pdf(path)
            text = extracted or ""
        else:
            return []
        # Coalesce into ~100-word paragraphs
        words = text.split()
        paragraphs: List[str] = []
        cursor = 0
        block = 100
        while cursor < len(words):
            paragraphs.append(" ".join(words[cursor : cursor + block]))
            cursor += block
        return paragraphs
