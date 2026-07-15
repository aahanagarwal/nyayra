"""Tests for voice + document routes.

ffmpeg, live_audio (the websocket bridge), and the Gemini client are all
mocked — no live API calls, no real ffmpeg subprocess spawned.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api import documents as documents_module
from app.api import voice as voice_module
from app.clients import live_audio
from app.clients.keypool import KeyPool
from app.core.config import get_settings
from app.db.models import Attachment, Base
from app.db.session import get_session
from app.services import audio_bridge
from app.services import storage as storage_module


class _FakeProcess:
    def __init__(self, stdout: bytes, returncode: int = 0):
        self._stdout = stdout
        self.returncode = returncode

    async def communicate(self, input_bytes: bytes) -> tuple[bytes, bytes]:
        return self._stdout, b""


@pytest.mark.asyncio
async def test_transcribe_pipes_pcm16_16k_args(monkeypatch):
    captured_args: list[list[str]] = []

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured_args.append(list(args))
        return _FakeProcess(b"\x00\x01\x02\x03")

    async def fake_run_turn(*, pool, model, system, response_modalities, input_message):
        assert response_modalities == ["TEXT"]
        assert "realtimeInput" in input_message
        return [{"text": "hello world"}]

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(live_audio, "run_turn", fake_run_turn)

    pool = KeyPool.from_values(["fake-key"])
    text = await audio_bridge.transcribe(b"raw-audio-bytes", "audio/ogg", pool, get_settings())

    assert text == "hello world"
    ffmpeg_args = captured_args[0]
    assert ffmpeg_args[0] == "ffmpeg"
    assert "-ar" in ffmpeg_args
    assert "16000" in ffmpeg_args


def test_synthesize_route_returns_null_audio_url_on_failure(monkeypatch):
    async def fake_synthesize(text, lang, pool, settings):
        raise RuntimeError("live session boom")

    monkeypatch.setattr(voice_module.audio_bridge, "synthesize", fake_synthesize)

    app = FastAPI()
    app.include_router(voice_module.router)
    client = TestClient(app)

    resp = client.post("/api/voice/synthesize", json={"text": "hello", "lang": "en"})

    assert resp.status_code == 200
    assert resp.json() == {"audioUrl": None}


def test_parse_document_persists_attachment_and_returns_id(tmp_path, monkeypatch):
    class _FakeStorageSettings:
        storage_path = str(tmp_path / "storage")
        public_base_url = "http://testserver"

    monkeypatch.setattr(storage_module, "get_settings", lambda: _FakeStorageSettings())

    expected_summary = "This is an eviction notice demanding you vacate within 30 days."

    class _FakeGeminiClient:
        async def generate(self, *, model, prompt, images=None, **kwargs):
            return {"text": expected_summary}

    monkeypatch.setattr(documents_module, "get_client", lambda: _FakeGeminiClient())

    db_path = tmp_path / "test.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)

    async def _create_tables() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_session():
        async with test_session_maker() as session:
            yield session

    app = FastAPI()
    app.include_router(documents_module.router)
    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    resp = client.post(
        "/api/document/parse",
        files={"file": ("notice.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "image"
    assert body["summary"] == expected_summary
    assert body["id"]

    async def _fetch() -> Attachment | None:
        async with test_session_maker() as session:
            return await session.get(Attachment, body["id"])

    attachment = asyncio.run(_fetch())
    assert attachment is not None
    assert attachment.extracted_text == expected_summary
    assert attachment.kind == "image"
