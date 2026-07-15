"""ORM models for the Nyayra MVP schema.

SQLAlchemy 2.x async style: DeclarativeBase + Mapped/mapped_column.
Timestamps are epoch milliseconds (int), matching the frontend contract.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy import JSON as JSONType
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, default="New chat")
    lang: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)  # 'app' | 'whatsapp'
    wa_from: Mapped[str | None] = mapped_column(String, index=True, default=None)
    created_at: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer)
    deleted_at: Mapped[int | None] = mapped_column(Integer, default=None)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.seq",
    )
    drafts: Mapped[list["Draft"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # 'user' | 'assistant'
    text: Mapped[str | None] = mapped_column(Text, default=None)
    answer_json: Mapped[dict | None] = mapped_column(JSONType, default=None)
    council_json: Mapped[list | None] = mapped_column(JSONType, default=None)
    attachments_json: Mapped[list | None] = mapped_column(JSONType, default=None)
    lang: Mapped[str | None] = mapped_column(String, default=None)
    seq: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(Integer)
    wa_message_sid: Mapped[str | None] = mapped_column(String, unique=True, default=None)

    chat: Mapped["Chat"] = relationship(back_populates="messages")


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[int] = mapped_column(Integer)

    chat: Mapped["Chat"] = relationship(back_populates="drafts")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)  # 'image' | 'pdf' | 'audio'
    name: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    mime: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[int] = mapped_column(Integer)


class WaLog(Base):
    __tablename__ = "wa_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sid: Mapped[str] = mapped_column(String, unique=True)
    direction: Mapped[str] = mapped_column(String)  # 'in' | 'out'
    from_number: Mapped[str | None] = mapped_column(String, default=None)
    to_number: Mapped[str | None] = mapped_column(String, default=None)
    body: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[int] = mapped_column(Integer)
