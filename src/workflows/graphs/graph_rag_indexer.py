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
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional, Set, Tuple

from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
from neo4j import Session

from config.settings import get_settings
from database.neo4j.client import neo4j_session


EMBED_MODEL = "text-embedding-3-large"  # 3072 dims


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
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
        self.create_vector_index = create_vector_index
        self.embed_dim = 3072

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
        with neo4j_session() as session:
            for t in triples:
                session.run(
                    """
                    MERGE (a:Entity {name: $head})
                    MERGE (b:Entity {name: $tail})
                    MERGE (a)-[r:RELATION {type: $rel}]->(b)
                    ON CREATE SET r.created_at = timestamp()
                    SET r.source = $source, r.chunk_id = $chunk_id
                    """,
                    head=t.head.strip(),
                    rel=t.relation.strip(),
                    tail=t.tail.strip(),
                    source=source,
                    chunk_id=chunk_id,
                )
                touched.add(t.head.strip())
                touched.add(t.tail.strip())
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
        for i in range(0, len(names), batch_size):
            batch = names[i : i + batch_size]
            embeds = self.client.embeddings.create(model=EMBED_MODEL, input=batch)
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
        return total

    def index_json_files(
        self,
        paths: List[Path],
        recursive: bool = True,
        max_chunks_per_file: Optional[int] = None,
        embed_entities: bool = True,
    ) -> IndexStats:
        stats = IndexStats()
        proc_cfg = self.settings.processing
        files: List[Path] = []
        for p in paths:
            p = Path(p)
            if p.is_file() and p.suffix.lower() == ".json":
                files.append(p)
            elif p.is_dir():
                files.extend(list(p.rglob("*.json") if recursive else p.glob("*.json")))
        seen_entities: Set[str] = set()
        for fp in files:
            try:
                text_blocks = self._prepare_text_blocks_from_json(fp)
                chunks = chunk_text(
                    "\n".join(text_blocks),
                    words_per_chunk=proc_cfg.chunk_size,
                    overlap_words=proc_cfg.chunk_overlap,
                )
                if max_chunks_per_file is not None:
                    chunks = chunks[:max_chunks_per_file]
                for idx, chunk in enumerate(chunks):
                    triples = self._extract_triples_llm(chunk)
                    touched = self._ingest_triples(triples, source=str(fp), chunk_id=idx)
                    seen_entities.update(touched)
                    stats.chunks_processed += 1
                    stats.triples_extracted += len(triples)
                stats.files_processed += 1
            except Exception:
                continue
        if embed_entities and seen_entities:
            stats.nodes_embedded = self._embed_entities(list(seen_entities))
        return stats

    def _prepare_text_blocks_from_json(self, path: Path) -> List[str]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        lines = flatten_json(data)
        # Coalesce into readable paragraphs (~80-100 words each) to keep LLM context efficient
        words = " ".join(lines).split()
        paragraphs: List[str] = []
        cursor = 0
        block = 100
        while cursor < len(words):
            paragraphs.append(" ".join(words[cursor : cursor + block]))
            cursor += block
        return paragraphs
