"""FastAPI app factory — wires every router together.

PIPELINE (for context, implemented elsewhere — see app/pipeline/orchestrator.py):
  PREP(fused mask PII + HyDE rewrite + route + lang + domain)
    -> ACT_SELECT -> COUNCIL(advocate+opposition; +devils_advocate+bench if complex)
    -> VERIFY(claims vs verbatim statute text; NEVER skipped; fail closed)
    -> UNMASK -> answer -> DRAFT(only if artifact requested)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat, chats, config_route, documents, drafts, system, voice, whatsapp
from app.api.errors import error_response
from app.clients.gemini import GeminiClient
from app.clients.keypool import KeyPool
from app.core.config import get_settings
from app.db.session import init_db
from app.retrieval.curated import get_retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nyayra")

# Stages whose models come from Settings.model_for(stage); audio/embed are
# separate fixed-purpose models with no per-stage council override.
_ROSTER_STAGES = ["prep", "act_select", "council", "verify", "unmask", "draft"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    await init_db()
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)

    # Same objects the routes use — a second pool here would keep its own
    # cooldown state and rotation would diverge per-module.
    from app.api.deps import get_client, get_pool

    pool = get_pool()
    client = get_client()
    retriever = get_retriever()

    app.state.key_pool = pool
    app.state.gemini_client = client
    app.state.retriever = retriever

    roster = ", ".join(f"{stage}={settings.model_for(stage)}" for stage in _ROSTER_STAGES)
    logger.info(
        "Nyayra starting — model roster: %s, audio=%s, embed=%s (%d key(s) in pool)",
        roster,
        settings.model_audio,
        settings.model_embed,
        len(pool.keys),
    )

    yield

    await client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Nyayra", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (
        chat.router,
        chats.router,
        drafts.router,
        config_route.router,
        voice.router,
        documents.router,
        whatsapp.router,
        system.router,
    ):
        app.include_router(router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(exc.detail, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception on %s %s", request.method, request.url.path)
        return error_response({"code": "internal", "message": "internal server error"}, status_code=500)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
