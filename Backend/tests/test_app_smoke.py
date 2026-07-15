"""End-to-end smoke test against the real app (app.main.create_app()).

httpx ASGITransport drives the ASGI app directly; the app's own lifespan is
driven manually (ASGITransport doesn't speak the lifespan protocol) so
startup/shutdown singleton wiring is exercised too. The DB is swapped for an
in-memory StaticPool sqlite via dependency_overrides on get_session — same
pattern as tests/test_chat_route.py — and the pipeline itself
(app.pipeline.orchestrator.run_pipeline_collect / run_pipeline) is
monkeypatched at the app.api.chat module level. No live Gemini calls.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import chat as chat_module
from app.db.models import Base
from app.db.session import get_session
from app.main import create_app
from app.schemas.chat import CouncilStage, LegalAnswer, Message

pytestmark = pytest.mark.asyncio


def _legal_answer() -> LegalAnswer:
    return LegalAnswer(
        rights=["You have a right to the return of your deposit"],
        options=["File a complaint", "Send a legal notice"],
        next_step=["Gather your rent receipts and the tenancy agreement"],
        needs_lawyer=False,
        lawyer_note=None,
    )


def _message(message_id: str = "msg-1") -> Message:
    return Message(
        id=message_id,
        role="assistant",
        answer=_legal_answer(),
        council=[CouncilStage(id="prep", label="Prep", role="prep", status="done")],
        lang="en",
        created_at=1_700_000_000_000,
    )


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with session_maker() as session:
            yield session

    async def fake_collect(*, text, lang, mode, attachments, client, retriever, settings):
        return _message().model_dump(by_alias=True)

    monkeypatch.setattr(chat_module, "run_pipeline_collect", fake_collect)

    app = create_app()
    app.dependency_overrides[get_session] = _get_session

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
            yield http_client

    await engine.dispose()


async def test_health(client):
    resp = await client.get("/api/system/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_config_includes_hindi(client):
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    assert "hi" in resp.json()["languages"]


async def test_models_shows_a_model_per_stage_and_key_pool_stats(client):
    resp = await client.get("/api/system/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["models"]["prep"]
    assert data["models"]["council"]
    assert isinstance(data["key_pool"], list)
    assert len(data["key_pool"]) >= 1


async def test_chats_list_starts_empty(client):
    resp = await client.get("/api/chats")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_send_message_round_trip_shows_up_in_chats(client):
    resp = await client.post(
        "/api/chat/message",
        json={
            "chatId": None,
            "text": "My landlord won't return my deposit",
            "lang": "en",
            "mode": "cloud",
            "attachmentIds": [],
        },
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # camelCase-on-the-wire contract guard.
    assert "nextStep" in data["answer"]
    assert "createdAt" in data

    chat_id = resp.headers["x-chat-id"]
    assert chat_id

    list_resp = await client.get("/api/chats")
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()]
    assert chat_id in ids

    detail_resp = await client.get(f"/api/chats/{chat_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == chat_id
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
