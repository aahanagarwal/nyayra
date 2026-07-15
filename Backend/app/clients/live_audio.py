"""Bridge to Gemini's native-audio model over its only interface: bidiGenerateContent.

gemini-2.5-flash-native-audio-latest supports ONLY the BidiGenerateContent
websocket RPC — there is no REST transcription/TTS endpoint for it. Each call
here opens a short-lived session, sends one turn, collects parts until
turnComplete, then closes. The server holds the API key; a client never sees
it.

VERIFIED WORKING SHAPE (do not deviate):
    url = wss://generativelanguage.googleapis.com/ws/
          google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=<key>
    send {"setup": {"model": "models/<model>",
                     "generationConfig": {"responseModalities": [...]},
                     "systemInstruction": {"parts": [{"text": ...}]}}}
    recv -> {"setupComplete": {}}
    send <input_message>   # e.g. {"realtimeInput": {"mediaChunks": [...]}}
    recv loop -> msg["serverContent"]["modelTurn"]["parts"][]
                 each {"text": ...} or {"inlineData": {...}}
                 until msg["serverContent"]["turnComplete"]
"""

from __future__ import annotations

import json
from typing import Literal

import websockets
from websockets.exceptions import InvalidStatus

from app.clients.keypool import KeyPool

_WS_URL_TMPL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={key}"
)
_KEY_ROTATE_STATUSES = (401, 403, 429)

Modality = Literal["TEXT", "AUDIO"]


async def run_turn(
    *,
    pool: KeyPool,
    model: str,
    system: str,
    response_modalities: list[Modality],
    input_message: dict,
) -> list[dict]:
    """Open a Live session, send one turn, return the modelTurn parts.

    Rotates keys on 401/403/429 exactly like the REST GeminiClient does,
    reporting status back to the pool so it cools bad keys.
    """
    max_attempts = max(len(pool.keys), 1)
    last_error: Exception = RuntimeError("live_audio: no keys available")

    for attempt in range(1, max_attempts + 1):
        key = await pool.acquire()
        url = _WS_URL_TMPL.format(key=key)
        try:
            async with websockets.connect(url, max_size=None) as ws:
                await ws.send(
                    json.dumps(
                        {
                            "setup": {
                                "model": f"models/{model}",
                                "generationConfig": {"responseModalities": response_modalities},
                                "systemInstruction": {"parts": [{"text": system}]},
                            }
                        }
                    )
                )
                await ws.recv()  # {"setupComplete": {}}

                await ws.send(json.dumps(input_message))

                parts: list[dict] = []
                async for raw in ws:
                    msg = json.loads(raw)
                    server_content = msg.get("serverContent", {})
                    parts.extend(server_content.get("modelTurn", {}).get("parts", []))
                    if server_content.get("turnComplete"):
                        break
                await pool.report(key, 200)
                return parts
        except InvalidStatus as exc:
            status = exc.response.status_code
            await pool.report(key, status)
            last_error = exc
            if status not in _KEY_ROTATE_STATUSES or attempt >= max_attempts:
                raise

    raise last_error
