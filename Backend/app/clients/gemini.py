"""Single choke point for every Gemini/Gemma model call.

Raw httpx against the REST API — not the google-genai SDK — because the SDK
binds a single key at client construction and we need to rotate keys
per-call through the KeyPool.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, AsyncIterator

import httpx

from app.clients.keypool import KeyPool

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_TIMEOUT_S = 30.0
_GEMMA_TIMEOUT_S = 90.0
_TRANSIENT_BACKOFF_S = 1.0
_KEY_ROTATE_STATUSES = (429, 401, 403)
_REPAIR_PROMPT = (
    "Your last response was not valid JSON matching the schema. "
    "Return ONLY valid JSON."
)


def _supports_thinking_budget(model: str) -> bool:
    """Gemma 400s if thinkingBudget is present at all; gemini wants it forced to 0."""
    return not model.startswith("gemma")


def _timeout_for(model: str) -> float:
    return _GEMMA_TIMEOUT_S if model.startswith("gemma") else _GEMINI_TIMEOUT_S


def _build_contents(prompt: str | list, images: list[tuple[bytes, str]] | None) -> list[dict]:
    """A bare string becomes a single user turn (+ any images inlined into it).

    A list is assumed to already be REST `contents` — multi-turn callers (e.g.
    the JSON-repair retry) build that shape themselves.
    """
    if isinstance(prompt, str):
        parts: list[dict] = [{"text": prompt}]
        for data, mime_type in images or []:
            parts.append(
                {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(data).decode("ascii")}}
            )
        return [{"role": "user", "parts": parts}]
    return list(prompt)


def _generation_config(
    *, model: str, max_output_tokens: int, temperature: float | None, schema: dict | None
) -> dict:
    config: dict[str, Any] = {"maxOutputTokens": max_output_tokens}
    if temperature is not None:
        config["temperature"] = temperature
    if _supports_thinking_budget(model):
        config["thinkingConfig"] = {"thinkingBudget": 0}
    if schema is not None:
        config["responseMimeType"] = "application/json"
        config["responseSchema"] = schema
    return config


def _build_body(
    *,
    model: str,
    prompt: str | list,
    system: str | None,
    schema: dict | None,
    images: list[tuple[bytes, str]] | None,
    max_output_tokens: int,
    temperature: float | None,
) -> dict:
    body: dict[str, Any] = {
        "contents": _build_contents(prompt, images),
        "generationConfig": _generation_config(
            model=model, max_output_tokens=max_output_tokens, temperature=temperature, schema=schema
        ),
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    return body


def _repair_contents(prompt: str | list, images: list[tuple[bytes, str]] | None, bad_text: str) -> list[dict]:
    contents = _build_contents(prompt, images)
    return contents + [
        {"role": "model", "parts": [{"text": bad_text}]},
        {"role": "user", "parts": [{"text": _REPAIR_PROMPT}]},
    ]


def _parts_of(data: dict) -> list[dict]:
    candidates = data.get("candidates") or []
    if not candidates:
        return []
    return candidates[0].get("content", {}).get("parts", []) or []


def _extract_text(data: dict, *, strip_thoughts: bool) -> tuple[str, dict]:
    texts = []
    for part in _parts_of(data):
        if strip_thoughts and part.get("thought"):
            continue
        if "text" in part:
            texts.append(part["text"])
    return "".join(texts), data.get("usageMetadata", {})


class GeminiClient:
    def __init__(self, pool: KeyPool, max_concurrent: int):
        self._pool = pool
        self._sem = asyncio.Semaphore(max_concurrent)
        self._http = httpx.AsyncClient()

    async def close(self) -> None:
        await self._http.aclose()

    async def _call(self, *, model: str, path: str, body: dict) -> dict:
        """POST with key rotation on 429/401/403 and one 1s-backoff retry on 5xx/timeout."""
        timeout = _timeout_for(model)
        url = f"{_API_BASE}/{model}:{path}"
        max_key_attempts = max(len(self._pool.keys), 1)
        retried_transient = False
        attempt = 0
        while True:
            attempt += 1
            key = await self._pool.acquire()
            async with self._sem:
                try:
                    resp = await self._http.post(url, params={"key": key}, json=body, timeout=timeout)
                except (httpx.TimeoutException, httpx.TransportError):
                    if retried_transient:
                        raise
                    retried_transient = True
                    await asyncio.sleep(_TRANSIENT_BACKOFF_S)
                    continue

            status = resp.status_code
            await self._pool.report(key, status)

            if status in _KEY_ROTATE_STATUSES:
                if attempt >= max_key_attempts:
                    resp.raise_for_status()
                continue

            if status >= 500:
                if retried_transient:
                    resp.raise_for_status()
                retried_transient = True
                await asyncio.sleep(_TRANSIENT_BACKOFF_S)
                continue

            resp.raise_for_status()
            return resp.json()

    async def generate(
        self,
        *,
        model: str,
        prompt: str | list,
        system: str | None = None,
        schema: dict | None = None,
        images: list[tuple[bytes, str]] | None = None,
        max_output_tokens: int = 8000,
        temperature: float | None = None,
    ) -> dict:
        body = _build_body(
            model=model,
            prompt=prompt,
            system=system,
            schema=schema,
            images=images,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
        data = await self._call(model=model, path="generateContent", body=body)
        text, usage = _extract_text(data, strip_thoughts=True)
        return {"text": text, "usage": usage, "model": model}

    async def generate_json(
        self,
        *,
        model: str,
        prompt: str | list,
        schema: dict,
        system: str | None = None,
        images: list[tuple[bytes, str]] | None = None,
        max_output_tokens: int = 8000,
        temperature: float | None = None,
    ) -> dict:
        result = await self.generate(
            model=model,
            prompt=prompt,
            system=system,
            schema=schema,
            images=images,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
        try:
            return json.loads(result["text"])
        except json.JSONDecodeError:
            pass

        repair_prompt = _repair_contents(prompt, images, result["text"])
        result = await self.generate(
            model=model,
            prompt=repair_prompt,
            system=system,
            schema=schema,
            images=None,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
        return json.loads(result["text"])  # second failure propagates

    async def stream(
        self,
        *,
        model: str,
        prompt: str | list,
        system: str | None = None,
        max_output_tokens: int = 8000,
    ) -> AsyncIterator[dict]:
        body = _build_body(
            model=model,
            prompt=prompt,
            system=system,
            schema=None,
            images=None,
            max_output_tokens=max_output_tokens,
            temperature=None,
        )
        timeout = _timeout_for(model)
        url = f"{_API_BASE}/{model}:streamGenerateContent"
        max_key_attempts = max(len(self._pool.keys), 1)

        for attempt in range(1, max_key_attempts + 1):
            key = await self._pool.acquire()
            async with self._sem:
                async with self._http.stream(
                    "POST", url, params={"key": key, "alt": "sse"}, json=body, timeout=timeout
                ) as resp:
                    if resp.status_code in _KEY_ROTATE_STATUSES:
                        await self._pool.report(key, resp.status_code)
                        if attempt >= max_key_attempts:
                            resp.raise_for_status()
                        continue

                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[len("data:") :].strip()
                        if not payload:
                            continue
                        chunk = json.loads(payload)
                        for part in _parts_of(chunk):
                            if "text" in part:
                                yield {"text": part["text"], "thought": bool(part.get("thought"))}
                    await self._pool.report(key, resp.status_code)
                    return

    async def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            body = {"content": {"parts": [{"text": text}]}}
            data = await self._call(model=model, path="embedContent", body=body)
            vectors.append(data.get("embedding", {}).get("values", []))
        return vectors
