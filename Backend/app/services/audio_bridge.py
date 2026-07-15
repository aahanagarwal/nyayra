"""ffmpeg <-> live_audio glue: arbitrary audio bytes <-> Gemini Live turns.

transcribe(): any audio container -> PCM16 mono 16kHz raw -> Live session
(TEXT modality) -> verbatim transcript.
synthesize(): text -> Live session (AUDIO modality) -> concatenated PCM16
24kHz -> ogg/opus bytes.
"""

from __future__ import annotations

import asyncio
import base64

from app.clients import live_audio
from app.clients.keypool import KeyPool
from app.core.config import Settings

_TRANSCRIBE_PROMPT = "Transcribe this audio verbatim. Return only the transcript text, nothing else."
_SYNTHESIZE_SYSTEM_TMPL = "Speak the following text aloud, naturally and clearly, in {lang}."
_LANG_NAMES = {"en": "English", "hi": "Hindi", "ta": "Tamil", "bn": "Bengali"}


async def _run_ffmpeg(args: list[str], input_bytes: bytes) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input_bytes)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {stderr.decode(errors='replace')}")
    return stdout


async def _to_pcm16_16k(audio_bytes: bytes) -> bytes:
    return await _run_ffmpeg(
        ["-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
        audio_bytes,
    )


async def _pcm16_24k_to_ogg(pcm_bytes: bytes) -> bytes:
    return await _run_ffmpeg(
        ["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0", "-c:a", "libopus", "-f", "ogg", "pipe:1"],
        pcm_bytes,
    )


def _audio_input_message(mime_type: str, data_b64: str) -> dict:
    return {"realtimeInput": {"mediaChunks": [{"mimeType": mime_type, "data": data_b64}]}}


def _text_input_message(text: str) -> dict:
    return {"clientContent": {"turns": [{"role": "user", "parts": [{"text": text}]}], "turnComplete": True}}


async def transcribe(audio_bytes: bytes, mime: str, pool: KeyPool, settings: Settings) -> str:
    """Any audio (mime is the upload's declared content-type; ffmpeg autodetects the
    actual container from the stream) -> verbatim transcript via the Live model."""
    pcm = await _to_pcm16_16k(audio_bytes)
    parts = await live_audio.run_turn(
        pool=pool,
        model=settings.model_audio,
        system=_TRANSCRIBE_PROMPT,
        response_modalities=["TEXT"],
        input_message=_audio_input_message("audio/pcm;rate=16000", base64.b64encode(pcm).decode("ascii")),
    )
    return "".join(part["text"] for part in parts if "text" in part).strip()


async def synthesize(text: str, lang: str, pool: KeyPool, settings: Settings) -> bytes:
    parts = await live_audio.run_turn(
        pool=pool,
        model=settings.model_audio,
        system=_SYNTHESIZE_SYSTEM_TMPL.format(lang=_LANG_NAMES.get(lang, lang)),
        response_modalities=["AUDIO"],
        input_message=_text_input_message(text),
    )
    pcm = b"".join(base64.b64decode(part["inlineData"]["data"]) for part in parts if "inlineData" in part)
    if not pcm:
        raise RuntimeError("synthesize: Live session returned no audio")
    return await _pcm16_24k_to_ogg(pcm)
