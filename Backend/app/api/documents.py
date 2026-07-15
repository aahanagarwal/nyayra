"""POST /api/document/parse, GET /api/files/{id}."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.gemini import GeminiClient
from app.clients.keypool import KeyPool
from app.core.config import Settings, get_settings
from app.db.models import Attachment
from app.db.session import get_session
from app.schemas.chat import ParseDocumentResponse
from app.schemas.common import now_ms
from app.services import storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])

_IMAGE_PROMPT = (
    "This image is a photo of a legal document or notice. In plain, simple "
    "language, summarize what kind of document this is and what it demands "
    "or requires the reader to do."
)
_PDF_PROMPT = (
    "This PDF is a legal document or notice. In plain, simple language, "
    "summarize what kind of document this is and what it demands or "
    "requires the reader to do."
)


from app.api.deps import get_client, get_pool  # shared, process-wide pool


def _kind_for(mime: str) -> str:
    return "pdf" if mime == "application/pdf" else "image"


async def _extract_summary(data: bytes, mime: str, kind: str, settings: Settings) -> str | None:
    prompt = _PDF_PROMPT if kind == "pdf" else _IMAGE_PROMPT
    try:
        result = await get_client().generate(
            model=settings.model_prep,
            prompt=prompt,
            images=[(data, mime)],
        )
        return result["text"].strip() or None
    except Exception:
        logger.exception("document summary extraction failed")
        return None


@router.post("/api/document/parse", response_model=ParseDocumentResponse)
async def parse_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> ParseDocumentResponse:
    mime = file.content_type or "application/octet-stream"
    kind = _kind_for(mime)
    data = await file.read()

    default_name = f"upload.{'pdf' if kind == 'pdf' else 'jpg'}"
    file_id = storage.save_bytes(data, file.filename or default_name)
    summary = await _extract_summary(data, mime, kind, settings)

    attachment = Attachment(
        id=file_id,
        kind=kind,
        name=file.filename or file_id,
        size_bytes=len(data),
        mime=mime,
        path=file_id,
        extracted_text=summary,
        created_at=now_ms(),
    )
    session.add(attachment)
    await session.commit()

    return ParseDocumentResponse(id=attachment.id, summary=summary, kind=kind)


@router.get("/api/files/{file_id}")
async def get_file(file_id: str) -> FileResponse:
    try:
        path = storage.full_path(file_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "internal", "message": str(exc)}) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail={"code": "internal", "message": "file not found"})
    return FileResponse(path)
