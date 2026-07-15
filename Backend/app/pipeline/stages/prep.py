"""PREP stage — one fused Flash call, then deterministic PII masking.

This is the airlock: everything downstream only ever sees `masked_text` (and
the masked `rewritten_query`) from the PrepResult this returns. If the model
call here raises, this function does NOT catch it — callers MUST treat that
as a hard stop and never process `text` further unmasked.
"""

from __future__ import annotations

from app.clients.gemini import GeminiClient
from app.core.config import Settings
from app.schemas.pipeline import PrepResult
from app.services import pii

_SUPPORTED_LANGS = {"en", "hi", "ta", "bn"}

_PREP_SCHEMA = {
    "type": "object",
    "properties": {
        "detected_lang": {"type": "string", "enum": ["en", "hi", "ta", "bn"]},
        "complexity": {"type": "string", "enum": ["simple", "complex"]},
        "requires_artifact": {"type": "boolean"},
        "domain": {"type": "string"},
        "rewritten_query": {"type": "string"},
        "pii_spans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "type": {"type": "string"},
                },
                "required": ["text", "type"],
            },
        },
    },
    "required": [
        "detected_lang",
        "complexity",
        "requires_artifact",
        "domain",
        "rewritten_query",
        "pii_spans",
    ],
}

_SYSTEM_PROMPT = (
    "You are the intake stage for an Indian legal-help assistant. Given the "
    "citizen's raw message, do ALL of the following in one pass:\n"
    "1. detected_lang: the language it is written in, one of en/hi/ta/bn.\n"
    "2. complexity: 'complex' if it involves multiple legal issues, criminal "
    "exposure, or conflicting parties; otherwise 'simple'.\n"
    "3. requires_artifact: true if the citizen is asking for a document to be "
    "drafted (a letter, complaint, application, notice), false otherwise.\n"
    "4. domain: a short label for the area of Indian law involved (e.g. "
    "'tenancy', 'consumer', 'criminal', 'motor_vehicles', 'domestic_violence').\n"
    "5. rewritten_query: rewrite the message as a hypothetical passage of "
    "Indian statute text that would answer it well — written in the register "
    "of an actual section of law, to maximise similarity with real statute "
    "text during retrieval.\n"
    "6. pii_spans: every person name mentioned in the message, verbatim as it "
    "appears in the message, each tagged type='name'. Do not include phone "
    "numbers, emails, Aadhaar numbers, or PAN numbers here — those are "
    "handled separately."
)


async def run_prep(client: GeminiClient, settings: Settings, text: str) -> PrepResult:
    """Raises on any model/parse failure — the caller must hard-stop, never
    fall back to processing `text` unmasked."""
    result = await client.generate_json(
        model=settings.model_for("prep"),
        prompt=text,
        system=_SYSTEM_PROMPT,
        schema=_PREP_SCHEMA,
    )

    names = [span["text"] for span in result["pii_spans"] if span.get("text")]
    masked_text, mask_map = pii.mask(text, names)
    # Also strip PII from the HyDE query before it flows into retrieval/council —
    # its own map is discarded since rewritten_query is never shown to the user
    # or unmasked later.
    masked_rewritten_query, _ = pii.mask(result["rewritten_query"], names)

    lang = result["detected_lang"] if result["detected_lang"] in _SUPPORTED_LANGS else "en"
    complexity = result["complexity"]
    requires_artifact = bool(result["requires_artifact"])
    council_size = 4 if (complexity == "complex" or requires_artifact) else 2

    return PrepResult(
        masked_text=masked_text,
        mask_map=mask_map,
        rewritten_query=masked_rewritten_query,
        lang=lang,
        complexity=complexity,
        requires_artifact=requires_artifact,
        domain=result["domain"],
        council_size=council_size,
    )
