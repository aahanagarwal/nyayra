"""Unit tests for GeminiClient — httpx is monkeypatched, no live API calls."""

from __future__ import annotations

import httpx
import pytest

from app.clients.gemini import GeminiClient
from app.clients.keypool import KeyPool


def _ok_payload(text: str = "hello") -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"totalTokenCount": 10},
    }


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}", request=httpx.Request("POST", "http://x"), response=None
            )


class FakeAsyncClient:
    """Drop-in for httpx.AsyncClient. Records calls, replays queued responses."""

    def __init__(self, *args, **kwargs):
        self.calls: list[dict] = []
        self.responses: list[FakeResponse] = []

    async def post(self, url, params=None, json=None, timeout=None):
        self.calls.append({"url": url, "params": dict(params or {}), "json": json})
        return self.responses.pop(0)

    async def aclose(self) -> None:
        pass


@pytest.fixture
def fake_http(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)


@pytest.mark.asyncio
async def test_thinking_budget_present_for_gemini_absent_for_gemma(fake_http):
    pool = KeyPool.from_values(["keyA"])
    client = GeminiClient(pool, max_concurrent=2)
    fake = client._http

    fake.responses = [FakeResponse(200, _ok_payload())]
    await client.generate(model="gemini-2.5-flash", prompt="hi")
    gemini_config = fake.calls[-1]["json"]["generationConfig"]
    assert gemini_config["thinkingConfig"]["thinkingBudget"] == 0

    fake.responses = [FakeResponse(200, _ok_payload())]
    await client.generate(model="gemma-4-26b-a4b-it", prompt="hi")
    gemma_config = fake.calls[-1]["json"]["generationConfig"]
    assert "thinkingConfig" not in gemma_config


@pytest.mark.asyncio
async def test_429_on_key_a_rotates_to_key_b_and_succeeds(fake_http):
    pool = KeyPool.from_values(["keyA", "keyB"])
    client = GeminiClient(pool, max_concurrent=2)
    fake = client._http

    fake.responses = [FakeResponse(429, {}), FakeResponse(200, _ok_payload("ok"))]
    result = await client.generate(model="gemini-2.5-flash", prompt="hi")

    assert result["text"] == "ok"
    assert fake.calls[0]["params"]["key"] == "keyA"
    assert fake.calls[1]["params"]["key"] == "keyB"


@pytest.mark.asyncio
async def test_generate_strips_thought_parts(fake_http):
    pool = KeyPool.from_values(["keyA"])
    client = GeminiClient(pool, max_concurrent=2)
    fake = client._http

    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "internal deliberation", "thought": True},
                        {"text": "final answer"},
                    ]
                }
            }
        ],
        "usageMetadata": {},
    }
    fake.responses = [FakeResponse(200, payload)]
    result = await client.generate(model="gemma-4-26b-a4b-it", prompt="hi")

    assert result["text"] == "final answer"
