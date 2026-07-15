"""Twilio REST client: send outbound WhatsApp messages, fetch inbound media.

Plain httpx against the REST API (same "no SDK client state" philosophy as
app/clients/gemini.py) — HTTP Basic auth with (account_sid, auth_token) on
every call, credentials read fresh from get_settings() so tests can
monkeypatch settings without touching module-level state.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings

_API_BASE = "https://api.twilio.com/2010-04-01"
_TIMEOUT_S = 30.0


async def send(to: str, body: str, media_url: str | None = None) -> dict:
    """POST a WhatsApp message via the Twilio Messages API."""
    settings = get_settings()
    url = f"{_API_BASE}/Accounts/{settings.twilio_account_sid}/Messages.json"
    form = {
        "To": to,
        "From": settings.twilio_whatsapp_from,
        "Body": body,
    }
    if media_url:
        form["MediaUrl"] = media_url

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            data=form,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_media(url: str) -> tuple[bytes, str]:
    """GET Twilio-hosted inbound media (MediaUrl0..), HTTP Basic auth."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "application/octet-stream")
        return resp.content, content_type
