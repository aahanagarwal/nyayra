"""GET /api/config — static capability descriptor for the frontend.

Doesn't exist elsewhere in the codebase; added here (main.py's author) since
main.py's router include list requires it. Values are the frontend contract's
own LangCode/Mode literals plus the feature set main.py actually wires up.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.chat import ConfigResponse

router = APIRouter(tags=["config"])

_LANGUAGES = ["en", "hi", "ta", "bn"]
_MODES = ["cloud", "local"]
_FEATURES = ["voice", "documents", "drafts", "whatsapp"]


@router.get("/api/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    return ConfigResponse(languages=_LANGUAGES, modes=_MODES, features=_FEATURES)
