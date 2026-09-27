"""Citation handling.

Maps numeric citation markers in the generated answer to the actual retrieved
chunks so the UI can render real, non-fabricated source cards. Every citation
shown to the user corresponds to a chunk that was truly retrieved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.rag.knowledge import Chunk

_CITE_RE = re.compile(r"\[(\d{1,2})\]")


@dataclass
class SourceCard:
    num: int
    title: str
    source: str
    source_url: str
    authority: str
    region: str
    excerpt: str
    license: str
    access_date: str

    def to_dict(self) -> dict:
        return {
            "num": self.num,
            "title": self.title,
            "source": self.source,
            "source_url": self.source_url,
            "authority": self.authority,
            "region": self.region,
            "excerpt": self.excerpt,
            "license": self.license,
            "access_date": self.access_date,
        }


def build_source_cards(cited: list[Chunk]) -> list[SourceCard]:
    cards: list[SourceCard] = []
    for i, c in enumerate(cited, start=1):
        excerpt = c.content.strip()
        if len(excerpt) > 320:
            excerpt = excerpt[:317].rstrip() + "..."
        cards.append(
            SourceCard(
                num=i,
                title=c.title or "Care guidance",
                source=c.source or "PetCare+ curated guidance",
                source_url=c.source_url or "",
                authority=c.authority or "",
                region=c.region or "",
                excerpt=excerpt,
                license=c.license or "",
                access_date=c.access_date or "",
            )
        )
    return cards


def extract_citation_nums(text: str) -> list[int]:
    return [int(m) for m in _CITE_RE.findall(text)]


def validate_citations(text: str, max_num: int) -> list[int]:
    """Return any citation numbers that exceed the available sources (fabricated)."""
    nums = extract_citation_nums(text)
    return [n for n in nums if n < 1 or n > max_num]


def normalize_citation_markers(text: str) -> str:
    """Ensure citation markers are spaced and consistent: [1] not [ 1 ]."""
    return re.sub(r"\[\s*(\d{1,2})\s*\]", lambda m: f"[{m.group(1)}]", text)
