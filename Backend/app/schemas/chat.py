"""Wire schemas for the chat/voice/document/config/chats/drafts API surface.

Mirrors the frontend TypeScript contract exactly (see FRONTEND CONTRACT).
camelCase on the wire, snake_case in python, via CamelModel.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel

LangCode = Literal["en", "hi", "ta", "bn"]
Mode = Literal["cloud", "local"]
Role = Literal["user", "assistant"]
CouncilStatus = Literal["done", "active", "pending"]
AttachmentKind = Literal["image", "pdf", "audio"]


class LegalAnswer(CamelModel):
    rights: list[str]
    options: list[str]
    next_step: list[str]
    needs_lawyer: bool | None = None
    lawyer_note: str | None = None


class CouncilStage(CamelModel):
    id: str
    label: str
    role: str
    status: CouncilStatus
    detail: str | None = None


class Attachment(CamelModel):
    id: str
    name: str
    kind: AttachmentKind
    size_label: str


class Message(CamelModel):
    id: str
    role: Role
    text: str | None = None
    answer: LegalAnswer | None = None
    council: list[CouncilStage] | None = None
    attachments: list[Attachment] | None = None
    lang: LangCode | None = None
    created_at: int
    pending: bool | None = None


class Chat(CamelModel):
    id: str
    title: str
    updated_at: int
    messages: list[Message]


class Draft(CamelModel):
    id: str
    title: str
    kind: str
    updated_at: int
    preview: str


# --- Request / response models -------------------------------------------------


class SendMessageRequest(CamelModel):
    chat_id: str | None = None
    text: str
    lang: LangCode = "en"
    mode: Mode = "cloud"
    attachment_ids: list[str] = Field(default_factory=list)


class TranscribeResponse(CamelModel):
    text: str


class SynthesizeRequest(CamelModel):
    text: str
    lang: LangCode


class SynthesizeResponse(CamelModel):
    audio_url: str | None = None


class ParseDocumentResponse(CamelModel):
    id: str
    summary: str | None = None
    kind: str


class ConfigResponse(CamelModel):
    languages: list[str]
    modes: list[str]
    features: list[str]
