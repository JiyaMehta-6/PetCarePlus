"""Knowledge base loading and access.

The runtime knowledge base is a single JSONL file (one semantic chunk per line)
plus a FAISS index. This module loads and exposes the chunks and provides
lightweight metadata helpers used by retrieval and metadata filtering.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import KNOWLEDGE_JSONL
from app.log_utils import get_logger

logger = get_logger("petcare.knowledge")


@dataclass
class Chunk:
    id: str
    species: list[str] = field(default_factory=list)
    breed: list[str] = field(default_factory=list)
    topic: str = ""
    subtopic: str = ""
    life_stage: list[str] = field(default_factory=list)
    title: str = ""
    content: str = ""
    source: str = ""
    source_url: str = ""
    license: str = ""
    access_date: str = ""
    authority: str = ""
    region: str = ""
    content_hash: str = ""

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.content}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "species": self.species,
            "breed": self.breed,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "life_stage": self.life_stage,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "source_url": self.source_url,
            "license": self.license,
            "access_date": self.access_date,
            "authority": self.authority,
            "region": self.region,
            "content_hash": self.content_hash,
        }


def load_chunks(path: Path | str = KNOWLEDGE_JSONL) -> list[Chunk]:
    path = Path(path)
    if not path.exists():
        logger.warning("Knowledge file not found: %s", path)
        return []
    chunks: list[Chunk] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSONL line %d: %s", lineno, exc)
                continue
            chunks.append(
                Chunk(
                    id=obj.get("id", f"chunk_{lineno}"),
                    species=obj.get("species", []) or [],
                    breed=obj.get("breed", []) or [],
                    topic=obj.get("topic", ""),
                    subtopic=obj.get("subtopic", ""),
                    life_stage=obj.get("life_stage", []) or [],
                    title=obj.get("title", ""),
                    content=obj.get("content", ""),
                    source=obj.get("source", ""),
                    source_url=obj.get("source_url", ""),
                    license=obj.get("license", ""),
                    access_date=obj.get("access_date", ""),
                    authority=obj.get("authority", ""),
                    region=obj.get("region", ""),
                    content_hash=obj.get("content_hash", ""),
                )
            )
    logger.info("Loaded %d knowledge chunks from %s", len(chunks), path)
    return chunks


def chunk_count(path: Path | str = KNOWLEDGE_JSONL) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())
