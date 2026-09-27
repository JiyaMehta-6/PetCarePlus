"""Hybrid retrieval: dense FAISS + BM25 + Reciprocal Rank Fusion.

The retriever loads the FAISS index once at startup, builds an in-memory BM25
index over the knowledge chunks, and fuses both rankings with RRF. Results are
then metadata-aware boosted (species / breed / life stage / topic) without
ever discarding the species-level knowledge that cross-cutting guidance relies
on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from app.config import (
    DENSE_TOP_K,
    BM25_TOP_K,
    RRF_K,
    FINAL_TOP_K,
    MIN_CONTEXT_CHUNKS,
    FAISS_INDEX,
    LOW_CONFIDENCE_THRESHOLD,
)
from app.log_utils import get_logger
from app.rag.bm25 import BM25
from app.rag.embeddings import EmbeddingModel
from app.rag.knowledge import Chunk, load_chunks
from app.rag.query_understanding import QueryContext
from app.rag.species_registry import TERM_TO_CLASS

logger = get_logger("petcare.retrieval")


@dataclass
class RetrievedChunk:
    chunk: Chunk
    dense_rank: int = 0
    bm25_rank: int = 0
    dense_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    meta_boost: float = 0.0
    final_score: float = 0.0


def _rrf_score(rank: int, k: int = RRF_K) -> float:
    if rank <= 0:
        return 0.0
    return 1.0 / (k + rank)


class FaissStore:
    def __init__(self, index_path: str = str(FAISS_INDEX)):
        self.index_path = index_path
        self.index = None
        self._ready = False

    def load(self) -> None:
        import faiss

        if not faiss.exists(self.index_path) if hasattr(faiss, "exists") else not __import__("os").path.exists(self.index_path):
            raise FileNotFoundError(f"FAISS index not found: {self.index_path}")
        self.index = faiss.read_index(self.index_path)
        self._ready = True
        logger.info("Loaded FAISS index (%d vectors, dim=%d)", self.index.ntotal, self.index.d)

    def search(self, vec: np.ndarray, k: int = DENSE_TOP_K):
        if not self._ready:
            self.load()
        vec = np.ascontiguousarray(vec, dtype=np.float32)
        if vec.ndim == 1:
            vec = vec.reshape(1, -1)
        k = min(k, self.index.ntotal)
        distances, indices = self.index.search(vec, k)
        return distances[0], indices[0]


class Retriever:
    def __init__(self, chunks: list[Chunk] | None = None, embedder: EmbeddingModel | None = None):
        self.chunks = chunks if chunks is not None else load_chunks()
        self.embedder = embedder
        self.faiss_store = FaissStore()
        self.bm25 = BM25()
        self._dense_cache: dict[str, np.ndarray] = {}
        self._build_bm25()

    def _build_bm25(self) -> None:
        texts = [c.text for c in self.chunks]
        self.bm25.build(texts)

    # -- lazy heavy resources ------------------------------------------------
    def ensure_faiss(self) -> None:
        if not self.faiss_store._ready:
            self.faiss_store.load()

    def ensure_embedder(self) -> EmbeddingModel:
        if self.embedder is None:
            self.embedder = EmbeddingModel()
        if not self.embedder._ready:
            self.embedder.load()
        return self.embedder

    # -- retrieval -----------------------------------------------------------
    def retrieve(self, ctx: QueryContext, final_k: int = FINAL_TOP_K) -> tuple[list[RetrievedChunk], float]:
        """Return fused, metadata-boosted chunks and a retrieval-confidence score."""
        embedder = self.ensure_embedder()
        self.ensure_faiss()

        qvec = embedder.encode(ctx.raw, is_query=True)
        self._dense_cache[ctx.raw] = qvec

        distances, indices = self.faiss_store.search(qvec, DENSE_TOP_K)
        dense_map: dict[int, tuple[int, float]] = {}
        for rank, (idx, dist) in enumerate(zip(indices, distances), start=1):
            if idx < 0:
                continue
            dense_map[idx] = (rank, float(dist))

        bm25_results = self.bm25.search(ctx.raw, BM25_TOP_K)
        bm25_map: dict[int, tuple[int, float]] = {}
        for rank, res in enumerate(bm25_results, start=1):
            bm25_map[res.index] = (rank, res.score)

        # Union of candidates from both legs.
        candidate_ids = set(dense_map) | set(bm25_map)
        fused: list[RetrievedChunk] = []
        for cid in candidate_ids:
            chunk = self.chunks[cid]
            d_rank, d_score = dense_map.get(cid, (10 ** 9, 0.0))
            b_rank, b_score = bm25_map.get(cid, (10 ** 9, 0.0))
            rrf = _rrf_score(d_rank) + _rrf_score(b_rank)
            meta_boost = self._meta_boost(chunk, ctx)
            fused.append(
                RetrievedChunk(
                    chunk=chunk,
                    dense_rank=d_rank,
                    bm25_rank=b_rank,
                    dense_score=d_score,
                    bm25_score=b_score,
                    rrf_score=rrf,
                    meta_boost=meta_boost,
                )
            )

        for f in fused:
            f.final_score = f.rrf_score + f.meta_boost

        fused.sort(key=lambda x: x.final_score, reverse=True)
        fused = self._dedupe(fused)

        k = max(final_k, MIN_CONTEXT_CHUNKS)
        selected = fused[:k]

        confidence = self._confidence(selected, ctx, dense_map)
        return selected, confidence

    def _meta_boost(self, chunk: Chunk, ctx: QueryContext) -> float:
        boost = 0.0
        if ctx.species:
            ctx_classes = set(ctx.species)
            chunk_classes = {TERM_TO_CLASS[t] for t in chunk.species if t in TERM_TO_CLASS}
            if chunk_classes & ctx_classes:
                # Same species/class as the pet -> strongly prioritise.
                boost += 0.05
            elif chunk_classes:
                # Specific to a *different* species/class -> demote so the answer
                # stays on-topic (cross-cutting "all species" chunks are kept).
                boost -= 0.045
            # else: untagged / cross-cutting -> neutral (still eligible)
        if ctx.breeds and chunk.breed:
            if any(b in chunk.breed for b in ctx.breeds):
                boost += 0.02
        if ctx.life_stage and chunk.life_stage:
            if any(ls in chunk.life_stage for ls in ctx.life_stage):
                boost += 0.006
        if ctx.topics and chunk.topic in ctx.topics:
            boost += 0.008
        if "india" in ctx.topics and chunk.region == "india":
            boost += 0.006
        return boost

    def _dedupe(self, fused: list[RetrievedChunk]) -> list[RetrievedChunk]:
        seen_hashes: set[str] = set()
        out: list[RetrievedChunk] = []
        for f in fused:
            h = f.chunk.content_hash or f.chunk.content[:80]
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            out.append(f)
        return out

    def _confidence(self, selected: list[RetrievedChunk], ctx: QueryContext, dense_map) -> float:
        if not selected:
            return 0.0
        best_cosine = max((f.dense_score for f in selected), default=0.0)
        # Map cosine (~0.1..0.8) onto 0..1.
        c = (best_cosine - 0.1) / 0.7
        c = max(0.0, min(1.0, c))
        if ctx.species:
            ctx_classes = set(ctx.species)
            for f in selected:
                chunk_classes = {TERM_TO_CLASS[t] for t in f.chunk.species if t in TERM_TO_CLASS}
                if chunk_classes & ctx_classes:
                    c = min(1.0, c + 0.1)
                    break
        if ctx.topics and any(f.chunk.topic in ctx.topics for f in selected):
            c = min(1.0, c + 0.05)
        return round(float(c), 3)

    @property
    def low_confidence(self) -> float:
        return LOW_CONFIDENCE_THRESHOLD
