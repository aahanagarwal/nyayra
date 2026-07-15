"""POST /api/chat/message — the single most important route.

Content-negotiated on Accept:
  - application/json (default, what the frontend uses today): runs the
    pipeline to completion via app.pipeline.orchestrator.run_pipeline_collect
    and returns the assistant Message.
  - text/event-stream: drains app.pipeline.orchestrator.run_pipeline (the
    async-generator orchestrator) and forwards its Events onto the wire as
    stage / answer_delta / done SSE frames, persisting the assistant message
    (and any draft) once the pipeline reaches a DoneEvent.

Two notes on how this reconciles with the FRONTEND CONTRACT:

1. The wire `Message` schema has no `chatId` field, yet "chatId null -> create
   chat server-side, return its server id" requires the caller learn that new
   id somehow. This route puts it on an `X-Chat-Id` response header (both
   paths) rather than inventing a field the frontend contract doesn't have.

2. `run_pipeline_collect` (owned by app/pipeline/orchestrator.py) drains the
   event stream and returns only the final DoneEvent's `message` dict — it
   discards `DoneEvent.draft`. So the JSON path here does not persist a Draft
   row even when PREP flagged `requires_artifact`; only the SSE path (which
   drains `run_pipeline` itself and sees the raw DoneEvent) does. Fixing that
   for the JSON path would mean draining `run_pipeline` here too instead of
   using the shared convenience function — left as-is since orchestrator.py
   isn't this file's to change and the frontend contract's own POST endpoint
   doc says this route returns a `Message`, not a Draft.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.gemini import GeminiClient
from app.clients.keypool import KeyPool
from app.core.config import Settings, get_settings
from app.db import repo
from app.db.models import Attachment as AttachmentRow
from app.db.session import get_session
from app.pipeline.events import AnswerDeltaEvent, DoneEvent, ErrorEvent, StageEvent
from app.pipeline.orchestrator import run_pipeline, run_pipeline_collect
from app.retrieval.base import Retriever
from app.retrieval.curated import get_retriever
from app.schemas.chat import Attachment, SendMessageRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

_PIPELINE_ERROR_RE = re.compile(r"^\[(?P<code>[a-z_]+)\]\s*(?P<message>.*)$", re.DOTALL)


from app.api.deps import get_client, get_pool  # shared, process-wide pool


# ---- small helpers ----------------------------------------------------------


def _size_label(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    kb = size_bytes / 1024
    if kb < 1024:
        return f"{kb:.0f} KB"
    return f"{kb / 1024:.1f} MB"


def _attachment_wire(row: AttachmentRow) -> Attachment:
    return Attachment(id=row.id, name=row.name, kind=row.kind, size_label=_size_label(row.size_bytes))


async def _load_attachments(session: AsyncSession, ids: list[str]) -> list[AttachmentRow]:
    if not ids:
        return []
    result = await session.execute(select(AttachmentRow).where(AttachmentRow.id.in_(ids)))
    rows = {row.id: row for row in result.scalars().all()}
    return [rows[i] for i in ids if i in rows]  # preserve request order; drop unknown ids


async def _resolve_chat(session: AsyncSession, chat_id: str | None, title_seed: str, lang: str):
    chat = await repo.get_chat(session, chat_id) if chat_id else None
    if chat is None:
        # Also covers a stale/unknown chat_id from the client: start a fresh
        # chat rather than 404ing on the single most important route.
        chat = await repo.create_chat(session, title=(title_seed[:40].strip() or "New chat"), lang=lang)
    return chat


def _drop_none(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def _parse_pipeline_error(exc: Exception) -> tuple[str, str]:
    """run_pipeline_collect raises RuntimeError("[code] message") on any
    pipeline failure (see its docstring) — recover the structured code."""
    match = _PIPELINE_ERROR_RE.match(str(exc))
    if match:
        return match.group("code"), match.group("message")
    return "internal", str(exc)


# ---- route ------------------------------------------------------------------


@router.post("/message")
async def send_message(
    request: Request,
    body: SendMessageRequest,
    settings: Settings = Depends(get_settings),
    client: GeminiClient = Depends(get_client),
    retriever: Retriever = Depends(get_retriever),
    session: AsyncSession = Depends(get_session),
):
    attachment_rows = await _load_attachments(session, body.attachment_ids)
    wire_attachments = [_attachment_wire(row) for row in attachment_rows] or None

    chat = await _resolve_chat(session, body.chat_id, body.text, body.lang)

    await repo.add_message(
        session,
        chat_id=chat.id,
        role="user",
        text=body.text,
        attachments_json=(
            [a.model_dump(by_alias=True) for a in wire_attachments] if wire_attachments else None
        ),
        lang=body.lang,
    )

    if "text/event-stream" in request.headers.get("accept", ""):
        return _sse_response(
            request=request,
            session=session,
            chat_id=chat.id,
            body=body,
            settings=settings,
            client=client,
            retriever=retriever,
            attachments=wire_attachments,
        )

    try:
        message_dict = await run_pipeline_collect(
            text=body.text,
            lang=body.lang,
            mode=body.mode,
            attachments=wire_attachments,
            client=client,
            retriever=retriever,
            settings=settings,
        )
    except Exception as exc:
        logger.exception("chat pipeline failed")
        code, msg = _parse_pipeline_error(exc)
        status_code = 429 if code == "rate_limited" else 500
        raise HTTPException(status_code=status_code, detail={"code": code, "message": msg}) from exc

    await repo.add_message(
        session,
        chat_id=chat.id,
        role="assistant",
        answer_json=message_dict.get("answer"),
        council_json=message_dict.get("council"),
        lang=message_dict.get("lang"),
    )

    return JSONResponse(content=_drop_none(message_dict), headers={"X-Chat-Id": chat.id})


def _sse_response(
    *,
    request: Request,
    session: AsyncSession,
    chat_id: str,
    body: SendMessageRequest,
    settings: Settings,
    client: GeminiClient,
    retriever: Retriever,
    attachments: list[Attachment] | None,
) -> StreamingResponse:
    async def event_source():
        seq = 0

        def frame(event_name: str, data: dict) -> bytes:
            nonlocal seq
            line = f"id: {seq}\nevent: {event_name}\ndata: {json.dumps(data)}\n\n"
            seq += 1
            return line.encode()

        gen = run_pipeline(
            text=body.text,
            lang=body.lang,
            mode=body.mode,
            attachments=attachments,
            client=client,
            retriever=retriever,
            settings=settings,
        )
        task: asyncio.Task | None = None
        last_done: DoneEvent | None = None
        persisted = False
        try:
            while True:
                if task is None:
                    task = asyncio.ensure_future(gen.__anext__())

                if await request.is_disconnected():
                    task.cancel()
                    with contextlib.suppress(BaseException):
                        await task
                    with contextlib.suppress(BaseException):
                        await gen.aclose()
                    return

                done, _pending = await asyncio.wait({task}, timeout=15.0)
                if not done:
                    yield b": hb\n\n"
                    continue

                try:
                    event = task.result()
                except StopAsyncIteration:
                    break
                except Exception as exc:  # defensive: orchestrator should already fail-closed
                    logger.exception("chat SSE pipeline failed")
                    yield frame("error", {"code": "internal", "message": str(exc)})
                    return
                task = None

                if isinstance(event, StageEvent):
                    yield frame("stage", event.stage.model_dump(by_alias=True, exclude_none=True))
                elif isinstance(event, AnswerDeltaEvent):
                    yield frame("answer_delta", {"field": event.field, "value": event.value})
                elif isinstance(event, ErrorEvent):
                    yield frame("error", {"code": event.code, "message": event.message})
                    return
                elif isinstance(event, DoneEvent):
                    # requires_artifact fans out into TWO DoneEvents (message,
                    # then message+draft) — persist the message once, persist
                    # the draft whenever one shows up, but only forward the
                    # wire `done` frame once, after the generator is fully
                    # drained, using whichever DoneEvent was last.
                    last_done = event
                    if not persisted:
                        message_dict = event.message.model_dump(by_alias=True, exclude_none=True)
                        await repo.add_message(
                            session,
                            chat_id=chat_id,
                            role="assistant",
                            answer_json=message_dict.get("answer"),
                            council_json=message_dict.get("council"),
                            lang=message_dict.get("lang"),
                        )
                        persisted = True
                    if event.draft:
                        await repo.add_draft(
                            session,
                            chat_id=chat_id,
                            title=event.draft.get("title", "Draft"),
                            kind=event.draft.get("kind", "document"),
                            body=event.draft.get("body_markdown", ""),
                        )
        except asyncio.CancelledError:
            if task is not None:
                task.cancel()
            raise

        if last_done is not None:
            yield frame("done", last_done.message.model_dump(by_alias=True, exclude_none=True))

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "X-Chat-Id": chat_id,
        },
    )
