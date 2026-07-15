"""Turn a pipeline result into outbound WhatsApp messages.

WhatsApp markdown only: *bold*, _italic_ — no headers, no tables (WhatsApp's
renderer doesn't support them).
"""

from __future__ import annotations

from typing import Any

from app.clients import twilio_client
from app.schemas.chat import LegalAnswer

ACK_TEXT = "On it — reviewing this under Indian law. May take a minute."

CHUNK_LIMIT = 1500


def format_answer(answer: LegalAnswer) -> str:
    """Render a LegalAnswer as WhatsApp-markdown text: rights, options, next step."""
    sections: list[str] = []

    if answer.rights:
        sections.append("*Your rights*\n" + "\n".join(f"- {r}" for r in answer.rights))

    if answer.options:
        sections.append("*Your options*\n" + "\n".join(f"- {o}" for o in answer.options))

    if answer.next_step:
        sections.append("*Next step*\n" + "\n".join(f"- {s}" for s in answer.next_step))

    if answer.needs_lawyer and answer.lawyer_note:
        sections.append(f"_{answer.lawyer_note}_")

    return "\n\n".join(sections)


def chunk(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Split text into <= limit-char pieces on paragraph ("\\n\\n") boundaries.

    Greedily packs whole paragraphs into each piece; a single paragraph
    longer than limit is hard-split as a last resort. Labels each piece
    "(i/n)" only when there's more than one.
    """
    paragraphs = text.split("\n\n")
    parts: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            parts.append(current)

        if len(para) <= limit:
            current = para
        else:
            for i in range(0, len(para), limit):
                parts.append(para[i : i + limit])
            current = ""

    if current:
        parts.append(current)

    if len(parts) <= 1:
        return parts

    total = len(parts)
    return [f"({i}/{total}) {part}" for i, part in enumerate(parts, start=1)]


async def send_ack(to: str) -> None:
    """Send the immediate "we got it" ack before the pipeline runs."""
    await twilio_client.send(to, ACK_TEXT)


async def send_result(to: str, result: Any) -> None:
    """Send the answer as its own message, then the draft (if any) as a follow-up."""
    for part in chunk(format_answer(result.answer)):
        await twilio_client.send(to, part)

    if result.draft:
        title = result.draft.get("title") or "Draft document"
        body = result.draft.get("body") or ""
        if body:
            for part in chunk(f"*{title}*\n\n{body}"):
                await twilio_client.send(to, part)
