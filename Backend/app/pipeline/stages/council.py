"""COUNCIL stage — concurrent multi-role legal argumentation over retrieved
statute chunks.

Each role sees the same masked query and statute context and independently
produces claims that (per its system prompt) must cite a citation_id present
in that context. Nothing here trusts a claim's citation — VERIFY re-checks
every one against the retriever's verbatim text.

Quorum: advocate + opposition are required. A role that raises is retried
ONCE if it's required; devils_advocate/bench are best-effort with no retry.
If both required roles ultimately fail, this raises.
"""

from __future__ import annotations

import asyncio

from app.clients.gemini import GeminiClient
from app.core.config import Settings
from app.retrieval.base import StatuteChunk
from app.schemas.pipeline import Claim, CouncilOpinion

REQUIRED_ROLES = {"advocate", "opposition"}

_ROLE_INSTRUCTIONS = {
    "advocate": "Make the citizen's strongest case. Argue for their rights and best options.",
    "opposition": (
        "Argue as the other party in this dispute (landlord, employer, police, "
        "company — whichever fits). Take their side against the citizen."
    ),
    "devils_advocate": "Attack the advocate's case. Find its weaknesses and counterarguments.",
    "bench": "Weigh the arguments neutrally, as a judge would, and note what actually matters.",
}

_CLAIM_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "citation_id": {"type": "string"},
                },
                "required": ["text", "citation_id"],
            },
        },
        "reasoning": {"type": "string"},
    },
    "required": ["claims", "reasoning"],
}


def _context_block(chunks: list[StatuteChunk]) -> str:
    if not chunks:
        return "No statute context available."
    return "\n".join(
        f"[{c.citation_id}] {c.act_name} s.{c.section_number} ({c.section_title}): {c.text}"
        for c in chunks
    )


def _system_prompt(role: str, chunks: list[StatuteChunk]) -> str:
    valid_ids = ", ".join(c.citation_id for c in chunks) or "(none)"
    return (
        f"You are the {role} in a legal council reasoning about an Indian "
        f"citizen's situation. {_ROLE_INSTRUCTIONS[role]}\n\n"
        "STATUTE CONTEXT:\n"
        f"{_context_block(chunks)}\n\n"
        f"Every claim you make MUST cite a citation_id from this exact set: "
        f"{valid_ids}. Never invent a citation_id. If no context section "
        "supports a point, omit that claim."
    )


async def _run_role(
    client: GeminiClient,
    settings: Settings,
    role: str,
    masked_query: str,
    chunks: list[StatuteChunk],
) -> CouncilOpinion:
    result = await client.generate_json(
        model=settings.model_for("council"),
        prompt=masked_query,
        system=_system_prompt(role, chunks),
        schema=_CLAIM_SCHEMA,
    )
    claims = [Claim(text=c["text"], citation_id=c["citation_id"]) for c in result["claims"]]
    return CouncilOpinion(role=role, claims=claims, reasoning=result["reasoning"])


async def run_council(
    client: GeminiClient,
    settings: Settings,
    masked_query: str,
    chunks: list[StatuteChunk],
    roles: list[str],
) -> tuple[list[CouncilOpinion], list[str]]:
    results = await asyncio.gather(
        *(_run_role(client, settings, role, masked_query, chunks) for role in roles),
        return_exceptions=True,
    )

    opinions: dict[str, CouncilOpinion] = {}
    failed: list[str] = []
    to_retry: list[str] = []

    for role, result in zip(roles, results):
        if isinstance(result, Exception):
            (to_retry if role in REQUIRED_ROLES else failed).append(role)
        else:
            opinions[role] = result

    if to_retry:
        retry_results = await asyncio.gather(
            *(_run_role(client, settings, role, masked_query, chunks) for role in to_retry),
            return_exceptions=True,
        )
        for role, result in zip(to_retry, retry_results):
            if isinstance(result, Exception):
                failed.append(role)
            else:
                opinions[role] = result

    if "advocate" in failed and "opposition" in failed:
        raise RuntimeError("council quorum failed: both advocate and opposition failed")

    ordered_opinions = [opinions[role] for role in roles if role in opinions]
    return ordered_opinions, failed
