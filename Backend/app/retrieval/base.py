"""Shared types for statute retrieval: data classes and the Retriever protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class StatuteChunk:
    citation_id: str
    act_id: str
    act_name: str
    section_number: str
    section_title: str
    text: str
    jurisdiction: str
    repealed: bool
    superseded_by: str | None
    source_url: str
    keywords: list[str]
    text_is_paraphrase: bool


@dataclass
class ActSummary:
    act_id: str
    act_name: str
    jurisdiction: str
    summary: str
    year: int
    repealed: bool


class Retriever(Protocol):
    def list_acts(self) -> list[ActSummary]: ...

    def search(
        self,
        query: str,
        act_ids: list[str] | None = None,
        top_k: int = 8,
        include_repealed: bool = False,
    ) -> list[StatuteChunk]: ...

    def get_by_citation(self, citation_id: str) -> StatuteChunk | None: ...
