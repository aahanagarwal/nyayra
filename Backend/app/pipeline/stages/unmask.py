"""UNMASK stage — pure functions; reverses PII placeholders in outbound content.

Called last, after VERIFY (and DRAFT, if run): every string the user will
actually see passes through services.pii.unmask so placeholders like
[PERSON_1] become the citizen's real name again.
"""

from __future__ import annotations

from app.schemas.chat import LegalAnswer
from app.services import pii


def unmask_answer(answer: LegalAnswer, mask_map: dict[str, str]) -> LegalAnswer:
    return LegalAnswer(
        rights=[pii.unmask(r, mask_map) for r in answer.rights],
        options=[pii.unmask(o, mask_map) for o in answer.options],
        next_step=[pii.unmask(s, mask_map) for s in answer.next_step],
        needs_lawyer=answer.needs_lawyer,
        lawyer_note=pii.unmask(answer.lawyer_note, mask_map) if answer.lawyer_note else answer.lawyer_note,
    )


def unmask_draft(draft: dict, mask_map: dict[str, str]) -> dict:
    unmasked = dict(draft)
    for key in ("title", "kind", "body_markdown"):
        value = unmasked.get(key)
        if isinstance(value, str):
            unmasked[key] = pii.unmask(value, mask_map)
    return unmasked
