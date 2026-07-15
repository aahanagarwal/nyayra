"""Statute retrieval: in-memory keyword search over the curated corpus."""

from app.retrieval.base import ActSummary, Retriever, StatuteChunk
from app.retrieval.curated import CuratedRetriever, get_retriever

__all__ = [
    "ActSummary",
    "Retriever",
    "StatuteChunk",
    "CuratedRetriever",
    "get_retriever",
]
