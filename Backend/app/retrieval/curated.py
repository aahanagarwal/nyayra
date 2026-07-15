"""In-memory retriever over the curated statute corpus (data/statutes/curated/*.json).

Every JSON file is loaded fully into memory at construction. Search is a simple,
case-insensitive token-overlap score across section title, body text, and keywords —
no embeddings, no external calls. Repealed sections are excluded from search by
default since citing repealed law as current is a correctness bug; get_by_citation
is an exact lookup regardless of repealed status (the verifier needs it either way,
e.g. to confirm an IPC->BNS supersession).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.retrieval.base import ActSummary, StatuteChunk

CURATED_DIR = Path(__file__).resolve().parents[2] / "data" / "statutes" / "curated"

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> Counter[str]:
    return Counter(_TOKEN_RE.findall(text.lower()))


class CuratedRetriever:
    """Loads every curated statute JSON file into memory at construction."""

    def __init__(self, curated_dir: Path = CURATED_DIR) -> None:
        self._acts: dict[str, ActSummary] = {}
        self._chunks: list[StatuteChunk] = []
        self._by_citation: dict[str, StatuteChunk] = {}

        for path in sorted(curated_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            act_id = data["act_id"]
            self._acts[act_id] = ActSummary(
                act_id=act_id,
                act_name=data["act_name"],
                jurisdiction=data["jurisdiction"],
                summary=data["summary"],
                year=data["year"],
                repealed=data["repealed"],
            )
            for section in data["sections"]:
                chunk = StatuteChunk(
                    citation_id=section["citation_id"],
                    act_id=act_id,
                    act_name=data["act_name"],
                    section_number=section["section_number"],
                    section_title=section["section_title"],
                    text=section["text"],
                    jurisdiction=data["jurisdiction"],
                    repealed=section["repealed"],
                    superseded_by=section.get("superseded_by"),
                    source_url=data["source_url"],
                    keywords=section.get("keywords", []),
                    text_is_paraphrase=section.get("text_is_paraphrase", False),
                )
                self._chunks.append(chunk)
                self._by_citation[chunk.citation_id] = chunk

    def list_acts(self) -> list[ActSummary]:
        return list(self._acts.values())

    def search(
        self,
        query: str,
        act_ids: list[str] | None = None,
        top_k: int = 8,
        include_repealed: bool = False,
    ) -> list[StatuteChunk]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, StatuteChunk]] = []
        for chunk in self._chunks:
            if not include_repealed and chunk.repealed:
                continue
            if act_ids is not None and chunk.act_id not in act_ids:
                continue

            title_tokens = _tokenize(chunk.section_title)
            text_tokens = _tokenize(chunk.text)
            keyword_tokens = _tokenize(" ".join(chunk.keywords))

            score = 0.0
            for token, q_count in query_tokens.items():
                score += q_count * (
                    3.0 * keyword_tokens.get(token, 0)
                    + 2.0 * title_tokens.get(token, 0)
                    + 1.0 * text_tokens.get(token, 0)
                )

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]

    def get_by_citation(self, citation_id: str) -> StatuteChunk | None:
        return self._by_citation.get(citation_id)


@lru_cache(maxsize=1)
def get_retriever() -> CuratedRetriever:
    return CuratedRetriever()
