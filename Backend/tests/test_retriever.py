"""Tests for app.retrieval.curated — loads the real corpus, no network/API calls."""

from __future__ import annotations

from app.retrieval.curated import get_retriever


def test_get_by_citation_returns_exact_text():
    retriever = get_retriever()
    chunk = retriever.get_by_citation("DRC-1958-S.14")
    assert chunk is not None
    assert chunk.citation_id == "DRC-1958-S.14"
    assert chunk.section_title == "Protection of tenant against eviction"
    assert "eviction" in chunk.keywords
    assert chunk.text.startswith(
        "Notwithstanding anything to the contrary contained in any other law"
    )


def test_get_by_citation_bogus_id_returns_none():
    retriever = get_retriever()
    assert retriever.get_by_citation("NOT-A-REAL-CITATION") is None


def test_search_eviction_notice_landlord_surfaces_delhi_rent_control():
    retriever = get_retriever()
    results = retriever.search("eviction notice landlord")
    assert results
    assert any(chunk.act_id == "delhi-rent-control-1958" for chunk in results)


def test_search_excludes_repealed_by_default():
    retriever = get_retriever()
    results = retriever.search("theft punishment", act_ids=["ipc-1860"])
    assert not any(chunk.act_id == "ipc-1860" for chunk in results)
    assert all(not chunk.repealed for chunk in results)


def test_search_includes_repealed_when_requested():
    retriever = get_retriever()
    results = retriever.search(
        "theft punishment", act_ids=["ipc-1860"], include_repealed=True
    )
    assert any(chunk.act_id == "ipc-1860" for chunk in results)
