"""GET /api/chats, GET /api/chats/{id}, PATCH /api/chats/{id}, DELETE /api/chats/{id}.

Doesn't exist elsewhere in the codebase; added here (main.py's author) since
main.py's router include list requires it. Converts app.db.models rows
(already written by app.db.repo) into the app.schemas.chat wire models —
no new persistence logic, just the read/rename/delete glue.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repo
from app.db.models import Chat as ChatRow, Message as MessageRow
from app.db.session import get_session
from app.schemas.chat import Attachment, Chat, CouncilStage, LegalAnswer, Message
from app.schemas.common import CamelModel

router = APIRouter(prefix="/api/chats", tags=["chats"])


class RenameChatRequest(CamelModel):
    title: str


def _message_wire(row: MessageRow) -> Message:
    return Message(
        id=row.id,
        role=row.role,
        text=row.text,
        answer=LegalAnswer.model_validate(row.answer_json) if row.answer_json else None,
        council=(
            [CouncilStage.model_validate(c) for c in row.council_json] if row.council_json else None
        ),
        attachments=(
            [Attachment.model_validate(a) for a in row.attachments_json]
            if row.attachments_json
            else None
        ),
        lang=row.lang,
        created_at=row.created_at,
    )


def _chat_wire(row: ChatRow, messages: list[Message]) -> Chat:
    return Chat(id=row.id, title=row.title, updated_at=row.updated_at, messages=messages)


@router.get("", response_model=list[Chat])
async def list_chats(session: AsyncSession = Depends(get_session)) -> list[Chat]:
    rows = await repo.list_chats(session)
    # list_chats() doesn't eager-load messages (see repo.py) — the contract
    # allows messages=[] here, so avoid touching the lazy relationship.
    return [_chat_wire(row, []) for row in rows]


@router.get("/{chat_id}", response_model=Chat)
async def get_chat(chat_id: str, session: AsyncSession = Depends(get_session)) -> Chat:
    row = await repo.get_chat(session, chat_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "internal", "message": "chat not found"})
    return _chat_wire(row, [_message_wire(m) for m in row.messages])


@router.patch("/{chat_id}", response_model=Chat)
async def rename_chat(
    chat_id: str, body: RenameChatRequest, session: AsyncSession = Depends(get_session)
) -> Chat:
    row = await repo.rename_chat(session, chat_id, body.title)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "internal", "message": "chat not found"})
    return _chat_wire(row, [])


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(chat_id: str, session: AsyncSession = Depends(get_session)) -> Response:
    await repo.soft_delete_chat(session, chat_id)
    return Response(status_code=204)
