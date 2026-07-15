"""Tests for the WhatsApp webhook — no live Twilio, no live Gemini.

Signature validation uses a real twilio.request_validator.RequestValidator on
both sides (test computes it the same way Twilio would). The pipeline runner
(_process_inbound) and the outbound Twilio client are monkeypatched so
nothing here makes a network call.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from twilio.request_validator import RequestValidator

from app.api import whatsapp
from app.db.models import Base
from app.db.session import get_session
from app.services import wa_adapter


class FakeSettings:
    twilio_auth_token = "test-auth-token"
    twilio_account_sid = "ACtest0000000000000000000000000"
    twilio_whatsapp_from = "whatsapp:+14155238886"
    public_base_url = "http://testserver"


BASE_FORM = {
    "MessageSid": "SM123",
    "AccountSid": FakeSettings.twilio_account_sid,
    "From": "whatsapp:+919876543210",
    "To": "whatsapp:+14155238886",
    "Body": "hello",
    "NumMedia": "0",
}

INBOUND_URL = "http://testserver/api/whatsapp/webhook/inbound"


def _signature(url: str, form: dict) -> str:
    return RequestValidator(FakeSettings.twilio_auth_token).compute_signature(url, form)


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setattr(whatsapp, "get_settings", lambda: FakeSettings())

    # StaticPool: aiosqlite's in-memory DB only exists on one connection, so
    # every checkout must reuse that same connection rather than opening a
    # fresh (empty) one.
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _create_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    async def _get_session():
        async with session_maker() as session:
            yield session

    app = FastAPI()
    app.include_router(whatsapp.router)
    app.dependency_overrides[get_session] = _get_session

    with TestClient(app) as client:
        yield client

    asyncio.run(engine.dispose())


def test_signed_post_returns_twiml_immediately(app_client, monkeypatch):
    calls = []

    async def fake_process(form):
        calls.append(form)

    monkeypatch.setattr(whatsapp, "_process_inbound", fake_process)

    sig = _signature(INBOUND_URL, BASE_FORM)
    resp = app_client.post(
        "/api/whatsapp/webhook/inbound",
        data=BASE_FORM,
        headers={"X-Twilio-Signature": sig},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/xml")
    assert resp.text == "<Response></Response>"
    assert len(calls) == 1


def test_bad_signature_returns_403(app_client, monkeypatch):
    async def fake_process(form):
        pass

    monkeypatch.setattr(whatsapp, "_process_inbound", fake_process)

    resp = app_client.post(
        "/api/whatsapp/webhook/inbound",
        data=BASE_FORM,
        headers={"X-Twilio-Signature": "not-the-right-signature"},
    )

    assert resp.status_code == 403


def test_duplicate_message_sid_does_not_rerun_pipeline(app_client, monkeypatch):
    calls = []

    async def fake_process(form):
        calls.append(form)

    monkeypatch.setattr(whatsapp, "_process_inbound", fake_process)

    headers = {"X-Twilio-Signature": _signature(INBOUND_URL, BASE_FORM)}

    first = app_client.post("/api/whatsapp/webhook/inbound", data=BASE_FORM, headers=headers)
    second = app_client.post("/api/whatsapp/webhook/inbound", data=BASE_FORM, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.text == "<Response></Response>"
    assert second.text == "<Response></Response>"
    assert len(calls) == 1


def test_chunk_splits_long_body_on_paragraph_boundaries():
    paragraphs = [
        f"Paragraph {i}: " + ("legal filler text describing rights and options. " * 4)
        for i in range(40)
    ]
    body = "\n\n".join(paragraphs)
    assert len(body) > 4000

    parts = wa_adapter.chunk(body, limit=1500)

    assert len(parts) > 1
    label_overhead = len(f"({len(parts)}/{len(parts)}) ")
    assert all(len(p) <= 1500 + label_overhead for p in parts)
    assert parts[0].startswith(f"(1/{len(parts)}) ")
    assert parts[-1].startswith(f"({len(parts)}/{len(parts)}) ")


def test_chunk_single_short_message_is_not_labeled():
    parts = wa_adapter.chunk("short answer, fits in one message")
    assert parts == ["short answer, fits in one message"]
