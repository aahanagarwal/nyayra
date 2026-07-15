"""ACT_SELECT stage — pick which Acts are relevant, then retrieve within them.

The model call only narrows down WHICH acts to search; the actual retrieval
is plain in-memory token-overlap search on the retriever (no model call).
"""

from __future__ import annotations

from app.clients.gemini import GeminiClient
from app.core.config import Settings
from app.retrieval.base import ActSummary, Retriever, StatuteChunk

_ACT_SELECT_SCHEMA = {
    "type": "object",
    "properties": {
        "selected_act_ids": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["selected_act_ids", "reasoning"],
}

_SYSTEM_TEMPLATE = (
    "You select which Indian Acts are relevant to a citizen's legal query, "
    "from the list of Acts below. Pick every Act that could plausibly apply; "
    "when unsure, include it rather than omit it. Only use act_id values "
    "from this list — never invent one.\n\n{acts_block}"
)


def _acts_block(acts: list[ActSummary]) -> str:
    if not acts:
        return "(no acts available)"
    lines = [
        f"- {a.act_id}: {a.act_name} ({a.jurisdiction}, {a.year})"
        f"{' [REPEALED]' if a.repealed else ''} — {a.summary}"
        for a in acts
    ]
    return "\n".join(lines)


async def run_act_select(
    client: GeminiClient,
    settings: Settings,
    retriever: Retriever,
    query: str,
    top_k: int = 8,
) -> list[StatuteChunk]:
    acts = retriever.list_acts()
    valid_ids = {a.act_id for a in acts}

    result = await client.generate_json(
        model=settings.model_for("act_select"),
        prompt=query,
        system=_SYSTEM_TEMPLATE.format(acts_block=_acts_block(acts)),
        schema=_ACT_SELECT_SCHEMA,
    )

    selected = [aid for aid in result["selected_act_ids"] if aid in valid_ids]
    # If the model selected nothing usable, fall back to searching every act
    # rather than returning zero context to COUNCIL/VERIFY.
    act_ids = selected or None

    return retriever.search(query, act_ids=act_ids, top_k=top_k)
