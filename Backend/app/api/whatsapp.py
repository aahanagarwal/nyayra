"""WhatsApp webhook endpoints — Twilio inbound messages + delivery status.

Twilio provisioning (phone number, sandbox, templates) is done by another
dev; this module only validates signatures, dedupes, replies to the webhook
immediately, and pushes the real answer back out via the Twilio REST API in
the background (the pipeline takes 30-150s — far too slow to hold the
webhook connection open).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator

from app.clients import twilio_client
from app.core.config import get_settings
from app.db import repo
from app.db.session import async_session_maker, get_session
from app.services import wa_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp/webhook", tags=["whatsapp"])

_NO_MEDIA_ANSWER = (
    "I've received your document, but I can't read attachments over WhatsApp "
    "yet — could you describe your question in a text message?"
)
_NO_VOICE_ANSWER = (
    "I couldn't process that voice note yet — could you type your question instead?"
)
_PIPELINE_ERROR_ANSWER = (
    "Sorry — something went wrong while looking into this. Please try again in a moment."
)


def _empty_twiml() -> Response:
    return Response(content="<Response></Response>", media_type="text/xml")


async def _validate_signature(request: Request, form: dict) -> None:
    settings = get_settings()
    if not settings.twilio_auth_token:
        logger.warning(
            "TWILIO_AUTH_TOKEN is empty — skipping inbound webhook signature "
            "validation. This is only acceptable for local development."
        )
        return

    signature = request.headers.get("X-Twilio-Signature", "")
    url = f"{settings.public_base_url.rstrip('/')}{request.url.path}"
    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, form, signature):
        raise HTTPException(status_code=403, detail="invalid Twilio signature")


@router.post("/inbound")
async def inbound_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Response:
    form = dict(await request.form())

    await _validate_signature(request, form)

    message_sid = form.get("MessageSid", "")
    from_number = form.get("From", "")

    if message_sid and await repo.seen_wa_sid(session, message_sid):
        return _empty_twiml()

    if message_sid:
        await repo.log_wa(
            session,
            sid=message_sid,
            direction="in",
            from_number=from_number,
            to_number=form.get("To"),
            body=form.get("Body"),
        )

    background_tasks.add_task(_process_inbound, form)

    return _empty_twiml()


@router.post("/status")
async def status_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    form = dict(await request.form())
    await _validate_signature(request, form)

    sid = form.get("MessageSid", "")
    if sid:
        error_code = form.get("ErrorCode")
        try:
            await repo.log_wa(
                session,
                sid=sid,
                direction="out",
                status=form.get("MessageStatus"),
                body=f"error_code={error_code}" if error_code else None,
            )
        except Exception:
            # WaLog.sid is unique but Twilio fires one callback per status
            # transition (queued -> sent -> delivered) for the *same* sid;
            # a second insert for a sid we've already logged is expected,
            # not a bug — swallow it rather than 500ing a Twilio webhook.
            await session.rollback()
            logger.info("status callback for already-logged sid=%s", sid)

    return Response(status_code=204)


def _classify_media(content_type: str) -> str:
    if content_type.startswith("audio/"):
        return "voice"
    return "document"  # image/* and application/pdf, plus anything unrecognized


async def _transcribe_or_none(data: bytes, content_type: str) -> str | None:
    """Best-effort voice transcription; degrades to None if audio_bridge isn't wired up."""
    try:
        from app.services.audio_bridge import transcribe
    except ImportError:
        logger.warning("app.services.audio_bridge not available — skipping voice transcription")
        return None
    try:
        return await transcribe(data, content_type)
    except Exception:
        logger.exception("voice transcription failed")
        return None


async def _run_pipeline_collect(text: str, lang: str = "en"):
    """Run the legal pipeline end-to-end and return the assistant message dict."""
    from app.api.deps import get_client, get_retriever
    from app.pipeline.orchestrator import run_pipeline_collect

    return await run_pipeline_collect(
        text=text,
        lang=lang,
        mode="cloud",
        attachments=None,
        client=get_client(),
        retriever=get_retriever(),
        settings=get_settings(),
    )


async def _process_inbound(form: dict) -> None:
    """Background task: ack, resolve media, run the pipeline, push the reply."""
    from_number = form.get("From", "")
    if not from_number:
        return

    await wa_adapter.send_ack(from_number)

    text = form.get("Body", "") or ""
    num_media = int(form.get("NumMedia") or "0")

    if num_media > 0 and form.get("MediaUrl0"):
        media_url = form["MediaUrl0"]
        declared_type = form.get("MediaContentType0", "")
        try:
            data, fetched_type = await twilio_client.fetch_media(media_url)
        except Exception:
            logger.exception("failed to fetch inbound media %s", media_url)
            data, fetched_type = b"", declared_type

        kind = _classify_media(fetched_type or declared_type)
        if kind == "voice":
            transcript = await _transcribe_or_none(data, fetched_type or declared_type)
            if transcript:
                text = f"{text}\n\n{transcript}".strip()
            elif not text:
                await twilio_client.send(from_number, _NO_VOICE_ANSWER)
                return
        elif not text:
            await twilio_client.send(from_number, _NO_MEDIA_ANSWER)
            return

    if not text:
        return

    async with async_session_maker() as session:
        chat = await repo.get_or_create_wa_chat(session, from_number)
        await repo.add_message(session, chat.id, role="user", text=text)

    try:
        result = await _run_pipeline_collect(text)
    except Exception:
        logger.exception("pipeline run failed for whatsapp message from %s", from_number)
        await twilio_client.send(from_number, _PIPELINE_ERROR_ANSWER)
        return

    async with async_session_maker() as session:
        chat = await repo.get_or_create_wa_chat(session, from_number)
        await repo.add_message(
            session,
            chat.id,
            role="assistant",
            answer_json=result.answer.model_dump(by_alias=True),
            lang=result.lang,
        )
        if result.draft:
            await repo.add_draft(
                session,
                chat.id,
                title=result.draft.get("title", "Draft"),
                kind=result.draft.get("kind", "document"),
                body=result.draft.get("body", ""),
            )

    await wa_adapter.send_result(from_number, result)
