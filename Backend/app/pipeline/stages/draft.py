"""DRAFT stage — only invoked when PREP set requires_artifact.

Generates the artifact (reply letter / complaint / application) in the
user's language, grounded in ONLY the verified answer and citations from
VERIFY — never in unverified council claims.
"""

from __future__ import annotations

import json

from app.clients.gemini import GeminiClient
from app.core.config import Settings
from app.schemas.chat import LegalAnswer

_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "kind": {"type": "string"},
        "body_markdown": {"type": "string"},
    },
    "required": ["title", "kind", "body_markdown"],
}

_SYSTEM_TEMPLATE = (
    "You draft a legal artifact (a reply letter, complaint, or application, "
    "whichever best fits) for an Indian citizen, in language code '{lang}'. "
    "Ground the draft ONLY in the rights, options, next steps, and citations "
    "given below — do not introduce any new legal claim. Write body_markdown "
    "as a complete, ready-to-send document in markdown. kind should be a "
    "short label such as 'reply_letter', 'complaint', or 'application'."
)


async def run_draft(
    client: GeminiClient,
    settings: Settings,
    answer: LegalAnswer,
    citations: list[dict],
    lang: str,
) -> dict:
    prompt = json.dumps(
        {
            "rights": answer.rights,
            "options": answer.options,
            "next_step": answer.next_step,
            "citations": citations,
        }
    )
    result = await client.generate_json(
        model=settings.model_for("draft"),
        prompt=prompt,
        system=_SYSTEM_TEMPLATE.format(lang=lang),
        schema=_DRAFT_SCHEMA,
    )
    return {
        "title": result["title"],
        "kind": result["kind"],
        "body_markdown": result["body_markdown"],
    }
