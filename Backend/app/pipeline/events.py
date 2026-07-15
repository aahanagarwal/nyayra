"""Internal pipeline events — transport-agnostic.

These are what `orchestrator.run_pipeline` yields. Both the SSE route and the
WhatsApp adapter consume this same stream and translate it onto their own
wire format; nothing here is a wire schema itself (see app/schemas/chat.py
for those).

`AnswerDeltaEvent.field` uses the wire-facing name 'nextStep' (not the
python-side `next_step`) because the SSE route forwards it onto the
`answer_delta` event's `field` value verbatim — see FRONTEND CONTRACT.

`DoneEvent.message` is the exact `Message` the `done` SSE event carries.
`DoneEvent.draft` is NOT part of that wire payload — a draft is its own
persisted resource (GET /api/drafts/{id}), so `draft` here is only a side
channel letting the caller (SSE route / WhatsApp adapter) persist it; it is
never one of the wire schema's own fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.chat import CouncilStage, Message

AnswerField = Literal["rights", "options", "nextStep"]


@dataclass
class StageEvent:
    stage: CouncilStage


@dataclass
class AnswerDeltaEvent:
    field: AnswerField
    value: str


@dataclass
class DoneEvent:
    message: Message
    draft: dict | None = None


@dataclass
class ErrorEvent:
    code: str
    message: str


Event = StageEvent | AnswerDeltaEvent | DoneEvent | ErrorEvent
