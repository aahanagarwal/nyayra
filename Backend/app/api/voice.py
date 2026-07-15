"""POST /api/voice/transcribe, POST /api/voice/synthesize."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.clients.keypool import KeyPool
from app.core.config import Settings, get_settings
from app.schemas.chat import SynthesizeRequest, SynthesizeResponse, TranscribeResponse
from app.services import audio_bridge, storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


from app.api.deps import get_pool  # shared, process-wide pool


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile = File(...),
    lang: str = Form("en"),
    settings: Settings = Depends(get_settings),
    pool: KeyPool = Depends(get_pool),
) -> TranscribeResponse:
    audio_bytes = await audio.read()
    mime = audio.content_type or "application/octet-stream"
    try:
        text = await audio_bridge.transcribe(audio_bytes, mime, pool, settings)
    except Exception as exc:
        logger.exception("voice transcribe failed")
        raise HTTPException(status_code=500, detail={"code": "internal", "message": str(exc)}) from exc
    return TranscribeResponse(text=text)


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(
    body: SynthesizeRequest,
    settings: Settings = Depends(get_settings),
    pool: KeyPool = Depends(get_pool),
) -> SynthesizeResponse:
    try:
        ogg_bytes = await audio_bridge.synthesize(body.text, body.lang, pool, settings)
    except Exception:
        logger.exception("voice synthesize failed")
        return SynthesizeResponse(audio_url=None)

    file_id = storage.save_bytes(ogg_bytes, "speech.ogg")
    return SynthesizeResponse(audio_url=storage.public_url(file_id))
