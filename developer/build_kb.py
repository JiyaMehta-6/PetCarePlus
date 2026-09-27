"""PetCare+ knowledge-base builder (developer tool).

Pipeline:
  1. Generate developer-curated, semantically chunked knowledge for the 30
     supported pet types across all required categories.
  2. Normalise and de-duplicate (SHA-256 exact + near-duplicate).
  3. Generate BGE-small embeddings on the D: drive.
  4. Build a single FAISS (IndexFlatIP, cosine) index.
  5. Write knowledge.jsonl + index.faiss + a build report.

Run with:
    python developer/build_kb.py

This is the ONLY place that needs internet (to download the embedding model
once). After the build, the runtime app is fully offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Ensure the project root is importable when run as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import (
    EMBEDDINGS_DIR,
    FAISS_INDEX,
    KNOWLEDGE_JSONL,
    KNOWLEDGE_DIR,
    configure_caches,
    ensure_directories,
)
from app.rag.embeddings import EmbeddingModel
from developer.kb_generators import build_all

CHUNKS: list[dict] = []


def add(chunk: dict):
    CHUNKS.append(chunk)

def ensure_bge_local():
    """Download BGE-small into the D: drive model directory if absent."""
    from huggingface_hub import snapshot_download
    if (EMBEDDINGS_DIR / "config.json").exists():
        return
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading embedding model to {EMBEDDINGS_DIR} ...")
    snapshot_download(
        "BAAI/bge-small-en-v1.5",
        local_dir=str(EMBEDDINGS_DIR),
        local_dir_use_symlinks=False,
    )


def main():
    configure_caches()
    ensure_directories()

    print("Generating knowledge chunks ...")
    build_all(add)

    # ---- deduplicate by exact content hash ----
    seen = set()
    unique = []
    removed = 0
    for c in CHUNKS:
        h = c["content_hash"]
        if h in seen:
            removed += 1
            continue
        seen.add(h)
        unique.append(c)
    print(f"Total generated: {len(CHUNKS)} | duplicates removed: {removed} | unique: {len(unique)}")

    # ---- assign stable ids ----
    for i, c in enumerate(unique, 1):
        sp = "_".join(c["species"]) if c["species"] else "general"
        br = ("_" + "_".join(c["breed"])) if c["breed"] else ""
        c["id"] = f"{sp}{br}_{i:05d}"

    # ---- embeddings ----
    ensure_bge_local()
    embedder = EmbeddingModel()
    embedder.load()
    texts = [f"{c['title']}\n\n{c['content']}" for c in unique]
    print(f"Embedding {len(texts)} chunks ...")
    vectors = embedder.encode(texts, is_query=False, batch_size=16)

    # ---- FAISS index (cosine via inner product on normalised vectors) ----
    import faiss
    index = faiss.IndexFlatIP(embedder.dim)
    index.add(vectors.astype("float32"))
    FAISS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX))

    # ---- write knowledge.jsonl ----
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    with KNOWLEDGE_JSONL.open("w", encoding="utf-8") as fh:
        for c in unique:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    report = {
        "chunk_count": len(unique),
        "duplicates_removed": removed,
        "embedding_dim": embedder.dim,
        "embedding_dtype": embedder.dtype,
        "faiss_index_type": "IndexFlatIP",
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "knowledge_jsonl": str(KNOWLEDGE_JSONL),
        "index_faiss": str(FAISS_INDEX),
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (KNOWLEDGE_DIR / "build_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("Build complete:")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
