"""GET /api/system/health, GET /api/system/models.

Doesn't exist elsewhere in the codebase; added here (main.py's author) since
main.py's router include list requires it. `models` builds its own KeyPool
via the same local @lru_cache pattern chat.py/documents.py/voice.py already
use (see chat.py's docstring on there being no shared app/api/deps.py) so
this endpoint's stats reflect this module's own pool the same way theirs do
— not app.main's separate startup singleton, which nothing here consumes.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends

from app.clients.keypool import KeyPool
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/system", tags=["system"])

_STAGES = ["prep", "act_select", "council", "verify", "unmask", "draft"]


from app.api.deps import get_pool  # shared, process-wide pool


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/models")
async def models(
    settings: Settings = Depends(get_settings),
    pool: KeyPool = Depends(get_pool),
) -> dict:
    roster = {stage: settings.model_for(stage) for stage in _STAGES}
    roster["audio"] = settings.model_audio
    roster["embed"] = settings.model_embed
    return {"models": roster, "key_pool": pool.stats()}
