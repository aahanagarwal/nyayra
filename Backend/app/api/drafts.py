"""GET /api/drafts, GET /api/drafts/{id}.

Doesn't exist elsewhere in the codebase; added here (main.py's author) since
main.py's router include list requires it. The wire `Draft` schema has no
separate "full body" field (see FRONTEND CONTRACT) — `preview` carries a
truncated snippet in the list view and the full draft body in the detail view.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repo
from app.db.models import Draft as DraftRow
from app.db.session import get_session
from app.schemas.chat import Draft

router = APIRouter(prefix="/api/drafts", tags=["drafts"])

_PREVIEW_LEN = 200


def _preview(body: str) -> str:
    return body if len(body) <= _PREVIEW_LEN else body[:_PREVIEW_LEN] + "…"


@router.get("", response_model=list[Draft])
async def list_drafts(session: AsyncSession = Depends(get_session)) -> list[Draft]:
    rows = await repo.list_drafts(session)
    return [
        Draft(id=row.id, title=row.title, kind=row.kind, updated_at=row.updated_at, preview=_preview(row.body))
        for row in rows
    ]


@router.get("/{draft_id}", response_model=Draft)
async def get_draft(draft_id: str, session: AsyncSession = Depends(get_session)) -> Draft:
    row: DraftRow | None = await repo.get_draft(session, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "internal", "message": "draft not found"})
    return Draft(id=row.id, title=row.title, kind=row.kind, updated_at=row.updated_at, preview=row.body)
