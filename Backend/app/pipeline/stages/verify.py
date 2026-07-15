"""VERIFY stage — the fail-closed gate between council claims and the answer.

Every claim's citation_id is checked against the retriever BEFORE any model
call: a citation the retriever doesn't recognise is a hallucination and is
rejected without spending a model call on it. Surviving (claim, verbatim
statute text) pairs go to one model call that judges support; a second,
schema'd call then synthesises the final LegalAnswer from ONLY the claims
that passed. This stage is never skipped. Any model failure here (after one
retry) raises — an unverified claim must never reach the user.
"""

from __future__ import annotations

import json

from app.clients.gemini import GeminiClient
from app.core.config import Settings
from app.retrieval.base import Retriever
from app.schemas.chat import LegalAnswer
from app.schemas.pipeline import Claim, CouncilOpinion, VerifyResult

_VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "verified": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_text": {"type": "string"},
                    "citation_id": {"type": "string"},
                    "supported": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["claim_text", "citation_id", "supported", "reason"],
            },
        },
    },
    "required": ["verified"],
}

_VERIFY_SYSTEM = (
    "You are a legal fact-checker. For each claim you are given the exact "
    "verbatim text of the statute section it cites. Judge ONLY whether that "
    "verbatim text actually supports the claim — do not use outside "
    "knowledge. If the statute text does not clearly support the claim, "
    "supported must be false."
)

_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "rights": {"type": "array", "items": {"type": "string"}},
        "options": {"type": "array", "items": {"type": "string"}},
        "next_step": {"type": "array", "items": {"type": "string"}},
        "needs_lawyer": {"type": "boolean"},
        "lawyer_note": {"type": "string"},
    },
    "required": ["rights", "options", "next_step", "needs_lawyer", "lawyer_note"],
}

_ANSWER_SYSTEM_TEMPLATE = (
    "You are drafting the final answer for an Indian citizen from ONLY the "
    "verified legal claims given below — do not add any claim that isn't "
    "listed there. Write in language code '{lang}'. Set needs_lawyer=true if "
    "there is criminal exposure, active litigation, or a limitation period "
    "about to expire; otherwise false. If needs_lawyer is false, "
    "lawyer_note must be an empty string."
)


async def _generate_json_fail_closed(
    client: GeminiClient, *, model: str, prompt: str, system: str, schema: dict
) -> dict:
    """One retry; if both attempts fail, raise — VERIFY must fail closed."""
    try:
        return await client.generate_json(model=model, prompt=prompt, system=system, schema=schema)
    except Exception:
        try:
            return await client.generate_json(
                model=model, prompt=prompt, system=system, schema=schema
            )
        except Exception as exc:
            raise RuntimeError(
                "VERIFY failed closed: model call failed twice, refusing to return "
                "unverified claims"
            ) from exc


async def run_verify(
    client: GeminiClient,
    settings: Settings,
    opinions: list[CouncilOpinion],
    retriever: Retriever,
    lang: str,
) -> tuple[VerifyResult, LegalAnswer]:
    all_claims: list[Claim] = [claim for opinion in opinions for claim in opinion.claims]

    checked: list[tuple[Claim, object]] = []
    rejected: list[dict] = []
    for claim in all_claims:
        chunk = retriever.get_by_citation(claim.citation_id)
        if chunk is None:
            rejected.append(
                {"claim_text": claim.text, "reason": "unknown citation_id (hallucinated)"}
            )
        else:
            checked.append((claim, chunk))

    verified_claims: list[Claim] = []
    citations_by_id: dict[str, dict] = {}

    if checked:
        pairs = [
            {"claim_text": claim.text, "citation_id": claim.citation_id, "statute_text": chunk.text}
            for claim, chunk in checked
        ]
        result = await _generate_json_fail_closed(
            client,
            model=settings.model_for("verify"),
            prompt=json.dumps(pairs),
            system=_VERIFY_SYSTEM,
            schema=_VERIFY_SCHEMA,
        )
        for item in result["verified"]:
            if item["supported"]:
                verified_claims.append(Claim(text=item["claim_text"], citation_id=item["citation_id"]))
                chunk = retriever.get_by_citation(item["citation_id"])
                if chunk is not None:
                    citations_by_id[chunk.citation_id] = {
                        "citation_id": chunk.citation_id,
                        "act_name": chunk.act_name,
                        "section_number": chunk.section_number,
                        "section_title": chunk.section_title,
                        "excerpt": chunk.text,
                    }
            else:
                rejected.append({"claim_text": item["claim_text"], "reason": item["reason"]})

    verify_result = VerifyResult(
        verified_claims=verified_claims,
        rejected=rejected,
        citations=list(citations_by_id.values()),
    )
    answer = await _synthesize_answer(client, settings, verified_claims, lang)
    return verify_result, answer


async def _synthesize_answer(
    client: GeminiClient, settings: Settings, verified_claims: list[Claim], lang: str
) -> LegalAnswer:
    prompt = json.dumps([{"text": c.text, "citation_id": c.citation_id} for c in verified_claims])
    result = await _generate_json_fail_closed(
        client,
        model=settings.model_for("verify"),
        prompt=prompt,
        system=_ANSWER_SYSTEM_TEMPLATE.format(lang=lang),
        schema=_ANSWER_SCHEMA,
    )
    return LegalAnswer(
        rights=result["rights"],
        options=result["options"],
        next_step=result["next_step"],
        needs_lawyer=result["needs_lawyer"],
        lawyer_note=result["lawyer_note"] or None,
    )
