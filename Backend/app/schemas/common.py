"""Shared base model and small helpers used across the wire schemas."""

from __future__ import annotations

import time

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


def now_ms() -> int:
    """Current time as epoch milliseconds (int)."""
    return int(time.time() * 1000)


class CamelModel(BaseModel):
    """Base for all wire models: python stays snake_case, JSON is camelCase."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ErrorBody(CamelModel):
    """Envelope for {"error": {"code", "message"}} error responses."""

    class _Error(CamelModel):
        code: str
        message: str

    error: _Error
