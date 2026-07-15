"""Tests for COUNCIL and VERIFY stages — GeminiClient is mocked, no live calls."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.pipeline.stages import council, verify
from app.retrieval.base import StatuteChunk

pytestmark = pytest.mark.asyncio


def _chunk(citation_id: str = "IPC-1860-S.378") -> StatuteChunk:
    return StatuteChunk(
        citation_id=citation_id,
        act_id="ipc-1860",
        act_name="Indian Penal Code, 1860",
        section_number="378",
        section_title="Theft - definition",
        text="Whoever, intending to take dishonestly any moveable property...",
        jurisdiction="IN",
        repealed=False,
        superseded_by=None,
        source_url="https://example.com",
        keywords=["theft"],
        text_is_paraphrase=False,
    )


def _claim_response(citation_id: str = "IPC-1860-S.378") -> dict:
    return {
        "claims": [{"text": "You may have a theft claim.", "citation_id": citation_id}],
        "reasoning": "Because of the facts given.",
    }


class FakeCouncilClient:
    """Resolves which role is calling by finding its name in the system prompt,
    then pops the next queued outcome (a dict result, or an Exception to raise)
    for that role."""

    def __init__(self, role_outcomes: dict[str, list]):
        self._outcomes = {role: list(outcomes) for role, outcomes in role_outcomes.items()}
        self.calls: list[str] = []

    async def generate_json(self, *, model, prompt, system, schema=None, **kwargs):
        role = next(r for r in self._outcomes if f"the {r} in a legal council" in system)
        self.calls.append(role)
        outcome = self._outcomes[role].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def test_council_proceeds_with_survivors_when_opposition_raises():
    settings = get_settings()
    client = FakeCouncilClient(
        {
            "advocate": [_claim_response()],
            "opposition": [RuntimeError("boom"), RuntimeError("boom again")],
        }
    )

    opinions, failed_roles = await council.run_council(
        client, settings, "masked query", [_chunk()], ["advocate", "opposition"]
    )

    assert failed_roles == ["opposition"]
    assert [o.role for o in opinions] == ["advocate"]
    # advocate called once, opposition called twice (initial + one retry)
    assert client.calls.count("advocate") == 1
    assert client.calls.count("opposition") == 2


async def test_council_raises_when_both_required_roles_fail():
    settings = get_settings()
    client = FakeCouncilClient(
        {
            "advocate": [RuntimeError("boom"), RuntimeError("boom again")],
            "opposition": [RuntimeError("boom"), RuntimeError("boom again")],
        }
    )

    with pytest.raises(RuntimeError):
        await council.run_council(
            client, settings, "masked query", [_chunk()], ["advocate", "opposition"]
        )


class FakeVerifyClient:
    """Routes by system prompt identity: the VERIFY classification call uses
    verify._VERIFY_SYSTEM verbatim; anything else is treated as the answer
    synthesis call."""

    def __init__(self, verify_outcomes: list | None = None, answer_result: dict | None = None):
        self._verify_outcomes = list(verify_outcomes or [])
        self._answer_result = answer_result or {
            "rights": [],
            "options": [],
            "next_step": [],
            "needs_lawyer": False,
            "lawyer_note": "",
        }
        self.calls: list[dict] = []

    async def generate_json(self, *, model, prompt, system, schema=None, **kwargs):
        self.calls.append({"system": system, "prompt": prompt})
        if system == verify._VERIFY_SYSTEM:
            outcome = self._verify_outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return self._answer_result


class FakeRetriever:
    def __init__(self, chunks: dict[str, StatuteChunk]):
        self._chunks = chunks

    def list_acts(self):
        return []

    def search(self, query, act_ids=None, top_k=8, include_repealed=False):
        return list(self._chunks.values())

    def get_by_citation(self, citation_id):
        return self._chunks.get(citation_id)


async def test_verify_rejects_bogus_citation_without_calling_the_model():
    settings = get_settings()
    client = FakeVerifyClient()
    retriever = FakeRetriever({})  # no known citations at all

    from app.schemas.pipeline import Claim, CouncilOpinion

    opinions = [
        CouncilOpinion(
            role="advocate",
            claims=[Claim(text="bogus claim", citation_id="NOT-A-REAL-CITATION")],
            reasoning="r",
        )
    ]

    verify_result, answer = await verify.run_verify(client, settings, opinions, retriever, "en")

    assert verify_result.verified_claims == []
    assert verify_result.rejected == [
        {"claim_text": "bogus claim", "reason": "unknown citation_id (hallucinated)"}
    ]
    # The verify classification model must never be called for a claim whose
    # citation couldn't be resolved.
    assert not any(call["system"] == verify._VERIFY_SYSTEM for call in client.calls)


async def test_verify_fails_closed_on_model_error():
    settings = get_settings()
    chunk = _chunk()
    client = FakeVerifyClient(verify_outcomes=[RuntimeError("boom"), RuntimeError("boom again")])
    retriever = FakeRetriever({chunk.citation_id: chunk})

    from app.schemas.pipeline import Claim, CouncilOpinion

    opinions = [
        CouncilOpinion(
            role="advocate",
            claims=[Claim(text="you may have a claim", citation_id=chunk.citation_id)],
            reasoning="r",
        )
    ]

    with pytest.raises(RuntimeError):
        await verify.run_verify(client, settings, opinions, retriever, "en")

    verify_calls = [c for c in client.calls if c["system"] == verify._VERIFY_SYSTEM]
    assert len(verify_calls) == 2  # initial attempt + one retry, then fail closed
