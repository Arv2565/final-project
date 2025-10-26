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
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional, Set, Tuple

from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
from neo4j import Session

from config.settings import get_settings
from database.neo4j.client import neo4j_session
from .enrichment import normalize_name, canonicalize_entities, enrich_relation, detect_doc_level_from_source
from .human_validation import flag_uncertain_triples
from utils.pdf_extractor import PDFTextExtractor


EMBED_MODEL = "text-embedding-3-large"  # 3072 dims

# Default OpenAI pricing (USD per 1K tokens). Override via env if needed.
DEFAULT_CHAT_INPUT_PER_1K = float(os.getenv("OPENAI_RATE_CHAT_INPUT_PER_1K", "5.00"))
DEFAULT_CHAT_OUTPUT_PER_1K = float(os.getenv("OPENAI_RATE_CHAT_OUTPUT_PER_1K", "15.00"))
DEFAULT_EMBED_PER_1K = float(os.getenv("OPENAI_RATE_EMBED_PER_1K", "0.13"))

logger = logging.getLogger(__name__)


class Triple(BaseModel):
    head: str = Field(..., description="Subject entity")
    relation: str = Field(..., description="Relationship type")
    tail: str = Field(..., description="Object entity")


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
    def __init__(self, create_vector_index: bool = True):
        self.settings = get_settings()
        self.client = OpenAI()
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.create_vector_index = create_vector_index
        self.embed_dim = 3072
        self.pdf_extractor = PDFTextExtractor()
        self.cost = CostStats()

    def _extract_triples_llm(self, text: str) -> List[Triple]:
        sys_prompt = (
            "You are a schema-aware extractor. Identify entities and relationships as triples. "
            "Return ONLY a valid JSON array, no commentary. Keys: head, relation, tail."
        )
        user_prompt = (
            "Extract entities and relationships as JSON triples from the following text.\n\n"
            f"Text:\n{text}\n\n"
            "Schema: [{\"head\": \"entity name\", \"relation\": \"relationship\", \"tail\": \"related entity\"}]"
        )
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
            data = []
        triples: List[Triple] = []
        for item in data:
            try:
                t = Triple(**item)
                # Basic sanitation
                if t.head and t.relation and t.tail:
                    triples.append(t)
            except ValidationError:
                continue
        return triples

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

    def _ingest_triples(self, triples: List[Triple], source: str, chunk_id: int) -> Set[str]:
        """Insert nodes/edges; return set of entity names touched."""
        touched: Set[str] = set()
        if not triples:
            return touched
        # Normalize and canonicalize entities to reduce node proliferation
        original_names = [t.head.strip() for t in triples if t.head] + [t.tail.strip() for t in triples if t.tail]
        name_to_canon, canon_groups = canonicalize_entities(original_names)

        law_level = detect_doc_level_from_source(source or "")

        with neo4j_session() as session:
            for t in triples:
                head_orig = t.head.strip()
                tail_orig = t.tail.strip()
                head = name_to_canon.get(head_orig, normalize_name(head_orig))
                tail = name_to_canon.get(tail_orig, normalize_name(tail_orig))
                enriched_rel = enrich_relation(t.relation.strip())

                # Merge nodes using canonical names, but keep a human-friendly display_name
                session.run(
                    """
                    MERGE (a:Entity {name: $head})
                    ON CREATE SET a.created_at = timestamp(), a.display_name = $head_orig
                    SET a.law_level = $law_level, a.source = $source

                    MERGE (b:Entity {name: $tail})
                    ON CREATE SET b.created_at = timestamp(), b.display_name = $tail_orig
                    SET b.law_level = $law_level, b.source = $source

                    MERGE (a)-[r:RELATION {type: $rel}]->(b)
                    ON CREATE SET r.created_at = timestamp(), r.source = $source, r.chunk_id = $chunk_id
                    SET r.relation_tag = $enriched_rel
                    """,
                    head=head,
                    head_orig=head_orig,
                    tail=tail,
                    tail_orig=tail_orig,
                    rel=t.relation.strip(),
                    enriched_rel=enriched_rel,
                    source=source,
                    chunk_id=chunk_id,
                    law_level=law_level,
                )
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
        batch_size = 128
        logger.info(f"Embedding {len(names)} unique entities in batches of {batch_size}...")
        start = time.time()
        for i in range(0, len(names), batch_size):
            batch = names[i : i + batch_size]
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
                    triples = self._extract_triples_llm(chunk)
                    # Human-in-the-loop: flag uncertain triples for review (does not block ingestion)
                    try:
                        flag_uncertain_triples([t.dict() for t in triples])
                    except Exception:
                        logger.debug("Failed to write review queue; continuing")
                    touched = self._ingest_triples(triples, source=str(fp), chunk_id=idx)
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
