"""Pipeline orchestrator — the async-generator heart of the request lifecycle.

PREP (fused mask PII + HyDE rewrite + route + lang + domain)
  -> ACT_SELECT -> COUNCIL (advocate+opposition; +devils_advocate+bench if complex)
  -> VERIFY (claims vs verbatim statute text; never skipped; fails closed)
  -> UNMASK -> answer -> DRAFT (only if an artifact was requested)

Yields transport-agnostic `Event`s (see app/pipeline/events.py) that both the
SSE route and the WhatsApp adapter consume and translate onto their own wire
formats.

NOTE on ACT_SELECT / COUNCIL concurrency: council's role prompts embed the
exact set of valid citation_ids drawn from the retrieved statute chunks (see
council._system_prompt / council._context_block), so council structurally
depends on act_select's output — it cannot start until act_select has
produced `chunks`. They therefore run sequentially here; the concurrency
that matters for latency happens *inside* council, across its roles
(advocate/opposition/devils_advocate/bench run concurrently via
asyncio.gather in council.run_council — four model calls against
act_select's one).

Every stage that can fail is wrapped so a raised exception becomes a clean
ErrorEvent + generator return instead of an unhandled exception blowing up
the SSE connection mid-stream. This mirrors PREP's and VERIFY's own
fail-closed contracts: nothing downstream of a failed stage ever runs, and
the generator always ends cleanly (one ErrorEvent, or one-or-two DoneEvents).
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from app.clients.gemini import GeminiClient
from app.clients.keypool import KeyPoolExhausted
from app.core.config import Settings
from app.pipeline.events import AnswerDeltaEvent, DoneEvent, ErrorEvent, Event, StageEvent
from app.pipeline.stages import act_select, council, draft, prep, unmask, verify
from app.retrieval.base import Retriever
from app.schemas.chat import Attachment, CouncilStage, Message
from app.schemas.common import now_ms

_SUPPORTED_LANGS = {"en", "hi", "ta", "bn"}

_STAGE_DISPLAY = {
    "prep": "Prep",
    "act_select": "Act Select",
    "verify": "Verify",
    "draft": "Draft",
}


def _label(stage: str, settings: Settings) -> str:
    return f"{_STAGE_DISPLAY[stage]} · {settings.model_for(stage)}"


def _roles_for(council_size: int) -> list[str]:
    if council_size >= 4:
        return ["advocate", "opposition", "devils_advocate", "bench"]
    return ["advocate", "opposition"]


def _error_code_for(exc: Exception) -> str:
    return "rate_limited" if isinstance(exc, KeyPoolExhausted) else "internal"


async def run_pipeline(
    *,
    text: str,
    lang: str,
    mode: str,
    attachments: list[Attachment] | None,
    client: GeminiClient,
    retriever: Retriever,
    settings: Settings,
) -> AsyncIterator[Event]:
    # `mode` ('cloud'|'local') has one implementation today: the cloud
    # GeminiClient the caller passes in. There is no separate on-device path
    # yet, so it's accepted (per the frontend contract) but unused here.
    # `attachments` is likewise accepted but not threaded into any stage —
    # none of the stage functions take image/document input today (YAGNI).
    del mode, attachments

    if lang not in _SUPPORTED_LANGS:
        yield ErrorEvent(code="unsupported_language", message=f"unsupported language: {lang!r}")
        return

    trace: dict[str, CouncilStage] = {}

    def emit(stage: CouncilStage) -> CouncilStage:
        trace[stage.id] = stage
        return stage

    # --- PREP ----------------------------------------------------------------
    yield StageEvent(stage=emit(CouncilStage(id="prep", label=_label("prep", settings), role="prep", status="active")))

    try:
        prep_result = await prep.run_prep(client, settings, text)
    except Exception as exc:  # hard stop — never process `text` unmasked further
        yield ErrorEvent(code="internal", message=f"prep failed: {exc}")
        return

    yield StageEvent(
        stage=emit(
            CouncilStage(
                id="prep",
                label=_label("prep", settings),
                role="prep",
                status="done",
                detail=f"lang={prep_result.lang}, complexity={prep_result.complexity}",
            )
        )
    )

    # --- ACT_SELECT ------------------------------------------------------------
    yield StageEvent(
        stage=emit(
            CouncilStage(id="act_select", label=_label("act_select", settings), role="act_select", status="active")
        )
    )

    try:
        chunks = await act_select.run_act_select(client, settings, retriever, prep_result.rewritten_query)
    except Exception as exc:
        yield ErrorEvent(code=_error_code_for(exc), message=f"act_select failed: {exc}")
        return

    yield StageEvent(
        stage=emit(
            CouncilStage(
                id="act_select",
                label=_label("act_select", settings),
                role="act_select",
                status="done",
                detail=f"{len(chunks)} statute chunks",
            )
        )
    )

    # --- COUNCIL -----------------------------------------------------------------
    roles = _roles_for(prep_result.council_size)
    council_label = f"Council · {settings.model_for('council')}"

    for role in roles:
        yield StageEvent(
            stage=emit(CouncilStage(id=f"council:{role}", label=council_label, role=role, status="active"))
        )

    try:
        opinions, failed_roles = await council.run_council(
            client, settings, prep_result.masked_text, chunks, roles
        )
    except Exception as exc:  # both required roles (advocate+opposition) failed
        yield ErrorEvent(code=_error_code_for(exc), message=f"council failed: {exc}")
        return

    opinions_by_role = {o.role: o for o in opinions}
    for role in roles:
        detail = (
            opinions_by_role[role].reasoning
            if role in opinions_by_role
            else "unavailable — model call failed after retry"
        )
        yield StageEvent(
            stage=emit(
                CouncilStage(id=f"council:{role}", label=council_label, role=role, status="done", detail=detail)
            )
        )

    # --- VERIFY (never skipped, fails closed) -------------------------------------
    yield StageEvent(
        stage=emit(CouncilStage(id="verify", label=_label("verify", settings), role="verify", status="active"))
    )

    try:
        verify_result, masked_answer = await verify.run_verify(client, settings, opinions, retriever, lang)
    except Exception as exc:
        yield ErrorEvent(code=_error_code_for(exc), message=f"verify failed: {exc}")
        return

    yield StageEvent(
        stage=emit(
            CouncilStage(
                id="verify",
                label=_label("verify", settings),
                role="verify",
                status="done",
                detail=(
                    f"{len(verify_result.verified_claims)} verified, "
                    f"{len(verify_result.rejected)} rejected"
                ),
            )
        )
    )

    # --- UNMASK -> answer ----------------------------------------------------------
    answer = unmask.unmask_answer(masked_answer, prep_result.mask_map)

    for field, values in (
        ("rights", answer.rights),
        ("options", answer.options),
        ("nextStep", answer.next_step),
    ):
        for value in values:
            yield AnswerDeltaEvent(field=field, value=value)

    message_id = str(uuid.uuid4())
    created_at = now_ms()
    message = Message(
        id=message_id,
        role="assistant",
        answer=answer,
        council=list(trace.values()),
        lang=lang,
        created_at=created_at,
    )
    yield DoneEvent(message=message)

    if not prep_result.requires_artifact:
        return

    # --- DRAFT (only when PREP flagged requires_artifact) ---------------------------
    yield StageEvent(
        stage=emit(CouncilStage(id="draft", label=_label("draft", settings), role="draft", status="active"))
    )

    try:
        masked_draft = await draft.run_draft(client, settings, masked_answer, verify_result.citations, lang)
    except Exception as exc:
        yield ErrorEvent(code=_error_code_for(exc), message=f"draft failed: {exc}")
        return

    draft_result = unmask.unmask_draft(masked_draft, prep_result.mask_map)

    yield StageEvent(
        stage=emit(
            CouncilStage(
                id="draft",
                label=_label("draft", settings),
                role="draft",
                status="done",
                detail=draft_result.get("title"),
            )
        )
    )

    final_message = Message(
        id=message_id,
        role="assistant",
        answer=answer,
        council=list(trace.values()),
        lang=lang,
        created_at=created_at,
    )
    yield DoneEvent(message=final_message, draft=draft_result)


async def run_pipeline_collect(
    *,
    text: str,
    lang: str,
    mode: str,
    attachments: list[Attachment] | None,
    client: GeminiClient,
    retriever: Retriever,
    settings: Settings,
) -> dict[str, Any]:
    """Drains `run_pipeline` and returns the last DoneEvent's message as a
    plain (already camelCase) dict — for the non-streaming JSON path
    (POST /api/chat/message without SSE) and the WhatsApp adapter.

    Raises RuntimeError if the pipeline hard-stopped on an ErrorEvent instead
    of ever reaching a DoneEvent — callers must not synthesize a fake success.
    """
    last_done: DoneEvent | None = None
    last_error: ErrorEvent | None = None

    async for event in run_pipeline(
        text=text,
        lang=lang,
        mode=mode,
        attachments=attachments,
        client=client,
        retriever=retriever,
        settings=settings,
    ):
        if isinstance(event, DoneEvent):
            last_done = event
        elif isinstance(event, ErrorEvent):
            last_error = event

    if last_done is None:
        code = last_error.code if last_error else "internal"
        message = last_error.message if last_error else "pipeline produced no result"
        raise RuntimeError(f"[{code}] {message}")

    return last_done.message.model_dump(by_alias=True)
