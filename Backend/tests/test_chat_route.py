"""Tests for POST /api/chat/message.

The pipeline itself (app.pipeline.orchestrator.run_pipeline_collect /
run_pipeline) is monkeypatched at the app.api.chat module level — no live
Gemini calls, no live retriever calls. The DB is a StaticPool in-memory
sqlite (same pattern as tests/test_whatsapp.py) wired in via FastAPI's
dependency_overrides.
"""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import chat as chat_module
from app.db.models import Base
from app.db.session import get_session
from app.pipeline.events import AnswerDeltaEvent, DoneEvent, StageEvent
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
async def app_and_client():
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

    app = FastAPI()
    app.include_router(chat_module.router)
    app.dependency_overrides[get_session] = _get_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    await engine.dispose()


async def test_json_path_returns_camel_case_message_and_creates_chat(app_and_client, monkeypatch):
    client = app_and_client

    async def fake_collect(*, text, lang, mode, attachments, client, retriever, settings):
        return _message().model_dump(by_alias=True)

    monkeypatch.setattr(chat_module, "run_pipeline_collect", fake_collect)

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
    assert data["role"] == "assistant"
    assert data["answer"]["nextStep"] == ["Gather your rent receipts and the tenancy agreement"]
    assert data["createdAt"] == 1_700_000_000_000

    chat_id = resp.headers["x-chat-id"]
    assert chat_id

    # chatId null created a chat server-side; sending the returned id back
    # must reuse the same chat rather than minting a new one.
    resp2 = await client.post(
        "/api/chat/message",
        json={
            "chatId": chat_id,
            "text": "follow-up question",
            "lang": "en",
            "mode": "cloud",
            "attachmentIds": [],
        },
        headers={"Accept": "application/json"},
    )
    assert resp2.status_code == 200
    assert resp2.headers["x-chat-id"] == chat_id


async def test_json_path_maps_rate_limited_to_429(app_and_client, monkeypatch):
    client = app_and_client

    async def fake_collect(**kwargs):
        raise RuntimeError("[rate_limited] all keys cooling")

    monkeypatch.setattr(chat_module, "run_pipeline_collect", fake_collect)

    resp = await client.post(
        "/api/chat/message",
        json={"chatId": None, "text": "hi", "lang": "en", "mode": "cloud", "attachmentIds": []},
    )

    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "rate_limited"


async def test_sse_path_emits_stage_then_answer_delta_then_done(app_and_client, monkeypatch):
    client = app_and_client

    async def fake_stream(*, text, lang, mode, attachments, client, retriever, settings):
        yield StageEvent(stage=CouncilStage(id="prep", label="Prep", role="prep", status="active"))
        yield StageEvent(stage=CouncilStage(id="prep", label="Prep", role="prep", status="done"))
        yield AnswerDeltaEvent(field="rights", value="You have a right to the return of your deposit")
        yield DoneEvent(message=_message(), draft=None)

    monkeypatch.setattr(chat_module, "run_pipeline", fake_stream)

    body = b""
    async with client.stream(
        "POST",
        "/api/chat/message",
        json={"chatId": None, "text": "question", "lang": "en", "mode": "cloud", "attachmentIds": []},
        headers={"Accept": "text/event-stream"},
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for chunk in resp.aiter_bytes():
            body += chunk

    frames = [f for f in body.decode().split("\n\n") if f.strip()]
    parsed = [dict(line.split(": ", 1) for line in f.splitlines()) for f in frames]

    assert [p["event"] for p in parsed] == ["stage", "stage", "answer_delta", "done"]

    ids = [int(p["id"]) for p in parsed]
    assert ids == list(range(len(ids)))  # seq monotonic from 0

    done_data = json.loads(parsed[-1]["data"])
    assert done_data["role"] == "assistant"
    assert done_data["answer"]["nextStep"] == ["Gather your rent receipts and the tenancy agreement"]
