"""Shared {"error": {"code", "message"}} error-response shape.

Routes across the app raise `HTTPException(status_code=..., detail=...)` with
`detail` either already a `{"code", "message"}` dict (chat.py, documents.py,
voice.py) or a plain string (whatsapp.py). `error_response` normalizes both
into the one wire envelope the frontend contract requires; app.main registers
it as the handler for HTTPException plus a catch-all for anything unhandled.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

_DEFAULT_CODE = "internal"


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def error_response(detail: Any, *, status_code: int) -> JSONResponse:
    """Build the {"error": {"code","message"}} JSON response for a given
    HTTPException.detail (or any other exception payload)."""
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        code, message = detail["code"], detail["message"]
    else:
        code, message = _DEFAULT_CODE, str(detail)
    return JSONResponse(status_code=status_code, content=error_body(code, message))
