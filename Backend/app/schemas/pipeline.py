"""Internal pipeline models — NOT wire schemas, no camelCase.

These flow between PREP -> ACT_SELECT/COUNCIL -> VERIFY -> UNMASK stages and
are never serialized directly to the frontend.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Complexity = Literal["simple", "complex"]


class PrepResult(BaseModel):
    masked_text: str
    mask_map: dict[str, str]
    rewritten_query: str
    lang: str
    complexity: Complexity
    requires_artifact: bool
    domain: str
    council_size: int


class Claim(BaseModel):
    text: str
    citation_id: str


class CouncilOpinion(BaseModel):
    role: str
    claims: list[Claim]
    reasoning: str


class VerifyResult(BaseModel):
    verified_claims: list[Claim]
    rejected: list[dict]
    citations: list[dict]
