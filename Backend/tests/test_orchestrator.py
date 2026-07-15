"""Tests for the pipeline orchestrator — every stage function is monkeypatched,
no live model or retriever calls happen anywhere in this file."""

from __future__ import annotations

import pytest

import app.pipeline.orchestrator as orchestrator
from app.core.config import get_settings
from app.pipeline.events import AnswerDeltaEvent, DoneEvent, ErrorEvent, StageEvent
from app.schemas.chat import LegalAnswer
from app.schemas.pipeline import Claim, CouncilOpinion, PrepResult, VerifyResult

pytestmark = pytest.mark.asyncio


def _prep_result(*, requires_artifact: bool = False, council_size: int = 2) -> PrepResult:
    return PrepResult(
        masked_text="masked facts",
        mask_map={"[PERSON_1]": "Ravi"},
        rewritten_query="rewritten statute-shaped query",
        lang="en",
        complexity="simple",
        requires_artifact=requires_artifact,
        domain="tenancy",
        council_size=council_size,
    )


def _verify_result_and_answer() -> tuple[VerifyResult, LegalAnswer]:
    verify_result = VerifyResult(
        verified_claims=[Claim(text="claim", citation_id="IPC-1860-S.378")],
        rejected=[],
        citations=[{"citation_id": "IPC-1860-S.378"}],
    )
    answer = LegalAnswer(
        rights=["right one"],
        options=["option one", "option two"],
        next_step=["step one"],
        needs_lawyer=False,
        lawyer_note=None,
    )
    return verify_result, answer


class _Calls:
    """Tiny call-tracker shared across the fakes in a single test."""

    def __init__(self):
        self.log: list[str] = []


def _install_happy_stages(monkeypatch, calls: _Calls, *, requires_artifact: bool):
    async def fake_run_prep(client, settings, text):
        calls.log.append("prep")
        return _prep_result(requires_artifact=requires_artifact)

    async def fake_run_act_select(client, settings, retriever, query, top_k=8):
        calls.log.append("act_select")
        return []

    async def fake_run_council(client, settings, masked_query, chunks, roles):
        calls.log.append("council")
        opinions = [
            CouncilOpinion(role=role, claims=[], reasoning=f"{role} reasoning") for role in roles
        ]
        return opinions, []

    async def fake_run_verify(client, settings, opinions, retriever, lang):
        calls.log.append("verify")
        return _verify_result_and_answer()

    async def fake_run_draft(client, settings, answer, citations, lang):
        calls.log.append("draft")
        return {"title": "Reply Letter", "kind": "reply_letter", "body_markdown": "Dear Sir..."}

    monkeypatch.setattr(orchestrator.prep, "run_prep", fake_run_prep)
    monkeypatch.setattr(orchestrator.act_select, "run_act_select", fake_run_act_select)
    monkeypatch.setattr(orchestrator.council, "run_council", fake_run_council)
    monkeypatch.setattr(orchestrator.verify, "run_verify", fake_run_verify)
    monkeypatch.setattr(orchestrator.draft, "run_draft", fake_run_draft)


async def _drain(**kwargs):
    settings = kwargs.pop("settings", get_settings())
    return [
        event
        async for event in orchestrator.run_pipeline(
            text=kwargs.pop("text", "my landlord won't return my deposit"),
            lang=kwargs.pop("lang", "en"),
            mode=kwargs.pop("mode", "cloud"),
            attachments=kwargs.pop("attachments", None),
            client=kwargs.pop("client", None),
            retriever=kwargs.pop("retriever", None),
            settings=settings,
        )
    ]


async def test_happy_path_yields_stages_in_order_then_done_with_no_draft(monkeypatch):
    calls = _Calls()
    _install_happy_stages(monkeypatch, calls, requires_artifact=False)

    events = await _drain()

    assert calls.log == ["prep", "act_select", "council", "verify"]

    stage_events = [e for e in events if isinstance(e, StageEvent)]
    stage_ids_in_order = [s.stage.id for s in stage_events]
    assert stage_ids_in_order == [
        "prep",
        "prep",
        "act_select",
        "act_select",
        "council:advocate",
        "council:opposition",
        "council:advocate",
        "council:opposition",
        "verify",
        "verify",
    ]
    # each stage goes active -> done
    for stage_id in {"prep", "act_select", "verify"}:
        statuses = [s.stage.status for s in stage_events if s.stage.id == stage_id]
        assert statuses == ["active", "done"]

    delta_events = [e for e in events if isinstance(e, AnswerDeltaEvent)]
    assert [(d.field, d.value) for d in delta_events] == [
        ("rights", "right one"),
        ("options", "option one"),
        ("options", "option two"),
        ("nextStep", "step one"),
    ]

    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert len(done_events) == 1
    assert done_events[0].draft is None
    assert done_events[0].message.answer.rights == ["right one"]
    assert [s.id for s in done_events[0].message.council] == [
        "prep",
        "act_select",
        "council:advocate",
        "council:opposition",
        "verify",
    ]

    # events end at the answer DoneEvent — draft stage never emitted, draft never invoked
    assert "draft" not in calls.log
    assert not any(isinstance(e, StageEvent) and e.stage.id == "draft" for e in events)
    assert events[-1] is done_events[0]


async def test_prep_failure_yields_error_and_stops_before_council(monkeypatch):
    calls = _Calls()

    async def failing_run_prep(client, settings, text):
        calls.log.append("prep")
        raise RuntimeError("model exploded")

    async def unexpected_run_act_select(*args, **kwargs):
        calls.log.append("act_select")
        raise AssertionError("act_select must never be invoked after a prep failure")

    async def unexpected_run_council(*args, **kwargs):
        calls.log.append("council")
        raise AssertionError("council must never be invoked after a prep failure")

    monkeypatch.setattr(orchestrator.prep, "run_prep", failing_run_prep)
    monkeypatch.setattr(orchestrator.act_select, "run_act_select", unexpected_run_act_select)
    monkeypatch.setattr(orchestrator.council, "run_council", unexpected_run_council)

    events = await _drain()

    assert calls.log == ["prep"]
    # the "prep active" stage event fires before the (failing) prep call
    assert len(events) == 2
    assert isinstance(events[0], StageEvent) and events[0].stage.id == "prep"
    assert events[0].stage.status == "active"
    assert isinstance(events[1], ErrorEvent)
    assert events[1].code == "internal"


async def test_no_artifact_requested_never_emits_draft_stage(monkeypatch):
    calls = _Calls()
    _install_happy_stages(monkeypatch, calls, requires_artifact=False)

    events = await _drain()

    assert "draft" not in calls.log
    assert not any(isinstance(e, StageEvent) and e.stage.id == "draft" for e in events)
    assert sum(isinstance(e, DoneEvent) for e in events) == 1


async def test_artifact_requested_emits_draft_stage_and_second_done_event(monkeypatch):
    calls = _Calls()
    _install_happy_stages(monkeypatch, calls, requires_artifact=True)

    events = await _drain()

    assert calls.log == ["prep", "act_select", "council", "verify", "draft"]

    draft_stage_events = [e for e in events if isinstance(e, StageEvent) and e.stage.id == "draft"]
    assert [s.stage.status for s in draft_stage_events] == ["active", "done"]

    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert len(done_events) == 2
    assert done_events[0].draft is None
    assert done_events[1].draft == {
        "title": "Reply Letter",
        "kind": "reply_letter",
        "body_markdown": "Dear Sir...",
    }
    # same logical message, updated in place
    assert done_events[0].message.id == done_events[1].message.id
    # the final trace includes the draft stage; the first one doesn't yet
    assert "draft" not in [s.id for s in done_events[0].message.council]
    assert "draft" in [s.id for s in done_events[1].message.council]
    assert events[-1] is done_events[1]


async def test_unsupported_language_short_circuits_before_prep(monkeypatch):
    calls = _Calls()

    async def unexpected_run_prep(*args, **kwargs):
        calls.log.append("prep")
        raise AssertionError("prep must never run for an unsupported language")

    monkeypatch.setattr(orchestrator.prep, "run_prep", unexpected_run_prep)

    events = await _drain(lang="fr")

    assert calls.log == []
    assert len(events) == 1
    assert isinstance(events[0], ErrorEvent)
    assert events[0].code == "unsupported_language"


async def test_council_quorum_failure_yields_error_and_stops_before_verify(monkeypatch):
    calls = _Calls()

    async def fake_run_prep(client, settings, text):
        return _prep_result()

    async def fake_run_act_select(client, settings, retriever, query, top_k=8):
        return []

    async def failing_run_council(client, settings, masked_query, chunks, roles):
        raise RuntimeError("council quorum failed: both advocate and opposition failed")

    async def unexpected_run_verify(*args, **kwargs):
        calls.log.append("verify")
        raise AssertionError("verify must never run after council fails")

    monkeypatch.setattr(orchestrator.prep, "run_prep", fake_run_prep)
    monkeypatch.setattr(orchestrator.act_select, "run_act_select", fake_run_act_select)
    monkeypatch.setattr(orchestrator.council, "run_council", failing_run_council)
    monkeypatch.setattr(orchestrator.verify, "run_verify", unexpected_run_verify)

    events = await _drain()

    assert calls.log == []
    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(error_events) == 1
    assert error_events[0].code == "internal"
    assert not any(isinstance(e, DoneEvent) for e in events)
