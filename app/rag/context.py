"""Context construction for the local LLM.

Takes the fused, metadata-boosted retrieval results and produces a compact,
budget-bounded context string plus a stable citation map. Duplicates and
near-identical chunks are removed and authoritative sources are prioritised so
the generator receives the cleanest possible evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import MAX_CONTEXT_TOKENS
from app.rag.knowledge import Chunk
from app.rag.retrieval import RetrievedChunk

# Authority tier weighting (higher = more authoritative).
_AUTHORITY_RANK = {
    "government": 1.0,
    "veterinary_guideline": 0.9,
    "veterinary_association": 0.85,
    "veterinary_manual": 0.8,
    "veterinary_university": 0.8,
    "research": 0.7,
    "developer_summary": 0.6,
    "other": 0.5,
}


def _tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.15))


def _near_identical(a: str, b: str) -> bool:
    # crude near-duplicate check on sentence overlap
    sa = set(re.findall(r"[a-z0-9 ]{12,}", a.lower()))
    sb = set(re.findall(r"[a-z0-9 ]{12,}", b.lower()))
    if not sa or not sb:
        return False
    overlap = len(sa & sb) / min(len(sa), len(sb))
    return overlap > 0.75


@dataclass
class ContextResult:
    context_text: str
    cited_chunks: list[Chunk] = field(default_factory=list)
    budget_used: int = 0


class ContextBuilder:
    def __init__(self, max_tokens: int = MAX_CONTEXT_TOKENS):
        self.max_tokens = max_tokens

    def build(self, results: list[RetrievedChunk]) -> ContextResult:
        # Re-rank by final score then authority, drop near-duplicates.
        ranked = sorted(
            results,
            key=lambda f: (f.final_score + _AUTHORITY_RANK.get(f.chunk.authority, 0.5) * 0.05),
            reverse=True,
        )

        chosen: list[RetrievedChunk] = []
        used_tokens = 0
        for f in ranked:
            if _near_identical_existing(f.chunk.content, chosen):
                continue
            t = _tokens(f.chunk.text)
            if used_tokens + t > self.max_tokens and chosen:
                break
            chosen.append(f)
            used_tokens += t

        cited: list[Chunk] = []
        blocks: list[str] = []
        for i, f in enumerate(chosen, start=1):
            cited.append(f.chunk)
            header = f"[{i}] {f.chunk.title}"
            meta = f"Source: {f.chunk.source or 'PetCare+ curated guidance'}"
            if f.chunk.authority:
                meta += f" ({f.chunk.authority})"
            if f.chunk.region:
                meta += f" | Region: {f.chunk.region}"
            blocks.append(f"{header}\n{meta}\n{f.chunk.content}")
        context_text = "\n\n---\n\n".join(blocks)
        return ContextResult(context_text=context_text, cited_chunks=cited, budget_used=used_tokens)


def _near_identical_existing(content: str, chosen: list[RetrievedChunk]) -> bool:
    for f in chosen:
        if _near_identical(content, f.chunk.content):
            return True
    return False
