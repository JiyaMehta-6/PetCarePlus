"""Lightweight BM25 lexical retrieval (Okapi BM25).

No external search engine. Pure-Python / NumPy implementation sufficient for a
few thousand knowledge chunks. Used as the lexical leg of hybrid retrieval and
fused with dense results via Reciprocal Rank Fusion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class BM25Result:
    index: int
    score: float


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avgdl = 0.0
        self.doc_lens = np.array([], dtype=np.float32)
        self.doc_freqs: list[dict[str, int]] = []
        self.idf: dict[str, float] = {}
        self.doc_index: list[int] = []  # maps bm25 order -> original chunk index

    @property
    def is_empty(self) -> bool:
        return self.doc_count == 0

    def build(self, texts: list[str], original_indices: list[int] | None = None) -> None:
        self.doc_index = list(original_indices) if original_indices else list(range(len(texts)))
        self.doc_count = len(texts)
        self.doc_freqs = []
        self.doc_lens = np.zeros(self.doc_count, dtype=np.float32)
        df: dict[str, int] = {}
        for i, text in enumerate(texts):
            toks = tokenize(text)
            self.doc_lens[i] = len(toks)
            freqs: dict[str, int] = {}
            for t in toks:
                freqs[t] = freqs.get(t, 0) + 1
            self.doc_freqs.append(freqs)
            for t in freqs:
                df[t] = df.get(t, 0) + 1
        self.avgdl = float(self.doc_lens.mean()) if self.doc_count else 0.0
        n = self.doc_count
        # idf with the standard BM25 smoothing term.
        self.idf = {
            term: np.log(1.0 + (n - df[term] + 0.5) / (df[term] + 0.5))
            for term in df
        }

    def search(self, query: str, top_k: int = 10) -> list[BM25Result]:
        if self.is_empty:
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        scores = np.zeros(self.doc_count, dtype=np.float32)
        for term in q_tokens:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, freqs in enumerate(self.doc_freqs):
                f = freqs.get(term, 0)
                if f == 0:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * self.doc_lens[i] / (self.avgdl or 1.0))
                scores[i] += idf * (f * (self.k1 + 1)) / denom
        if top_k is None or top_k >= self.doc_count:
            order = np.argsort(-scores)
        else:
            # Partial selection for efficiency on larger corpora.
            order = np.argpartition(-scores, top_k)[:top_k]
            order = order[np.argsort(-scores[order])]
        results = []
        for idx in order:
            if scores[idx] <= 0:
                break
            results.append(BM25Result(index=int(idx), score=float(scores[idx])))
            if len(results) >= top_k:
                break
        return results
