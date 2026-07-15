"""Pipeline orchestrator.

PREP (fused mask PII + HyDE rewrite + route + lang + domain)
  -> ACT_SELECT, then COUNCIL (advocate+opposition; +devils_advocate+bench if complex)
  -> VERIFY (claims vs verbatim statute text; never skipped; fails closed)
  -> UNMASK -> answer -> DRAFT (only if an artifact was requested)

NOTE on ACT_SELECT / COUNCIL concurrency: council's role prompts ground every
claim in a citation_id drawn from the retrieved statute chunks, so council
structurally depends on act_select's output — it cannot start until act_select
has produced `chunks`. We therefore run them sequentially at this top level;
the concurrency that matters for latency happens *inside* council, across its
roles (advocate/opposition/devils_advocate/bench run concurrently via
asyncio.gather in council.run_council) — that's four model calls, versus
act_select's one.

A PREP failure is a hard stop: it propagates out of this function uncaught.
Callers must never fall back to processing raw, unmasked text.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.clients.gemini import GeminiClient
from app.core.config import Settings
from app.pipeline.stages import act_select, council, draft, prep, unmask, verify
from app.retrieval.base import Retriever
from app.schemas.chat import LegalAnswer
from app.schemas.pipeline import CouncilOpinion


class PipelineResult(BaseModel):
    answer: LegalAnswer
    citations: list[dict]
    rejected: list[dict]
    council: list[CouncilOpinion]
    failed_roles: list[str]
    draft: dict | None
    lang: str
    domain: str


def _roles_for(council_size: int) -> list[str]:
    if council_size >= 4:
        return ["advocate", "opposition", "devils_advocate", "bench"]
    return ["advocate", "opposition"]


async def run_pipeline(
    client: GeminiClient,
    settings: Settings,
    retriever: Retriever,
    text: str,
) -> PipelineResult:
    prep_result = await prep.run_prep(client, settings, text)

    chunks = await act_select.run_act_select(
        client, settings, retriever, prep_result.rewritten_query
    )
    opinions, failed_roles = await council.run_council(
        client,
        settings,
        prep_result.masked_text,
        chunks,
        _roles_for(prep_result.council_size),
    )

    verify_result, masked_answer = await verify.run_verify(
        client, settings, opinions, retriever, prep_result.lang
    )

    answer = unmask.unmask_answer(masked_answer, prep_result.mask_map)

    draft_result = None
    if prep_result.requires_artifact:
        masked_draft = await draft.run_draft(
            client, settings, masked_answer, verify_result.citations, prep_result.lang
        )
        draft_result = unmask.unmask_draft(masked_draft, prep_result.mask_map)

    return PipelineResult(
        answer=answer,
        citations=verify_result.citations,
        rejected=verify_result.rejected,
        council=opinions,
        failed_roles=failed_roles,
        draft=draft_result,
        lang=prep_result.lang,
        domain=prep_result.domain,
    )
