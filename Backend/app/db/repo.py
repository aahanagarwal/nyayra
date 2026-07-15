"""Plain async data-access functions. Routes convert ORM objects -> schemas."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Chat, Draft, Message, WaLog


def _new_id() -> str:
    return uuid.uuid4().hex


def _now_ms() -> int:
    return int(time.time() * 1000)


# ---- chats ----------------------------------------------------------------


async def create_chat(
    session: AsyncSession,
    title: str = "New chat",
    lang: str = "en",
    channel: str = "app",
    wa_from: str | None = None,
) -> Chat:
    now = _now_ms()
    chat = Chat(
        id=_new_id(),
        title=title,
        lang=lang,
        channel=channel,
        wa_from=wa_from,
        created_at=now,
        updated_at=now,
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def get_chat(session: AsyncSession, chat_id: str) -> Chat | None:
    result = await session.execute(
        select(Chat)
        .where(Chat.id == chat_id, Chat.deleted_at.is_(None))
        .options(selectinload(Chat.messages))
    )
    return result.scalar_one_or_none()


async def list_chats(session: AsyncSession) -> list[Chat]:
    result = await session.execute(
        select(Chat).where(Chat.deleted_at.is_(None)).order_by(Chat.updated_at.desc())
    )
    return list(result.scalars().all())


async def rename_chat(session: AsyncSession, chat_id: str, title: str) -> Chat | None:
    chat = await session.get(Chat, chat_id)
    if chat is None or chat.deleted_at is not None:
        return None
    chat.title = title
    chat.updated_at = _now_ms()
    await session.commit()
    await session.refresh(chat)
    return chat


async def soft_delete_chat(session: AsyncSession, chat_id: str) -> None:
    chat = await session.get(Chat, chat_id)
    if chat is None:
        return
    now = _now_ms()
    chat.deleted_at = now
    chat.updated_at = now
    await session.commit()


# ---- messages ---------------------------------------------------------------


async def add_message(
    session: AsyncSession,
    chat_id: str,
    role: str,
    text: str | None = None,
    answer_json: dict | None = None,
    council_json: list | None = None,
    attachments_json: list | None = None,
    lang: str | None = None,
    wa_message_sid: str | None = None,
) -> Message:
    next_seq = await session.scalar(
        select(func.coalesce(func.max(Message.seq), 0) + 1).where(Message.chat_id == chat_id)
    )
    now = _now_ms()
    message = Message(
        id=_new_id(),
        chat_id=chat_id,
        role=role,
        text=text,
        answer_json=answer_json,
        council_json=council_json,
        attachments_json=attachments_json,
        lang=lang,
        seq=next_seq,
        created_at=now,
        wa_message_sid=wa_message_sid,
    )
    session.add(message)

    chat = await session.get(Chat, chat_id)
    if chat is not None:
        chat.updated_at = now

    await session.commit()
    await session.refresh(message)
    return message


# ---- drafts -----------------------------------------------------------------


async def list_drafts(session: AsyncSession) -> list[Draft]:
    result = await session.execute(select(Draft).order_by(Draft.updated_at.desc()))
    return list(result.scalars().all())


async def get_draft(session: AsyncSession, draft_id: str) -> Draft | None:
    return await session.get(Draft, draft_id)


async def add_draft(session: AsyncSession, chat_id: str, title: str, kind: str, body: str) -> Draft:
    now = _now_ms()
    draft = Draft(
        id=_new_id(),
        chat_id=chat_id,
        title=title,
        kind=kind,
        body=body,
        created_at=now,
        updated_at=now,
    )
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return draft


# ---- whatsapp -----------------------------------------------------------------


async def get_or_create_wa_chat(session: AsyncSession, wa_from: str) -> Chat:
    result = await session.execute(
        select(Chat).where(
            Chat.channel == "whatsapp",
            Chat.wa_from == wa_from,
            Chat.deleted_at.is_(None),
        )
    )
    chat = result.scalars().first()
    if chat is not None:
        return chat
    return await create_chat(session, title="WhatsApp", lang="en", channel="whatsapp", wa_from=wa_from)


async def seen_wa_sid(session: AsyncSession, sid: str) -> bool:
    result = await session.execute(select(WaLog.id).where(WaLog.sid == sid))
    return result.scalar_one_or_none() is not None


async def log_wa(
    session: AsyncSession,
    sid: str,
    direction: str,
    from_number: str | None = None,
    to_number: str | None = None,
    body: str | None = None,
    status: str | None = None,
) -> WaLog:
    entry = WaLog(
        id=_new_id(),
        sid=sid,
        direction=direction,
        from_number=from_number,
        to_number=to_number,
        body=body,
        status=status,
        created_at=_now_ms(),
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry
