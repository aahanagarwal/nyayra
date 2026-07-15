# Nyayra — WhatsApp Bot (Phase 1)

_Your Legal EA. Justice you can talk to._

A WhatsApp legal companion built on **whatsapp-web.js**, with a Gemma-native–style
cascading pipeline (mask → reason → verify → unmask). Phase 1 of the Nyayra design:
text + voice + document parsing, drafting, situation help, and recording analysis.

## What it does

| You send… | Nyayra does… |
|---|---|
| A **text question / situation** (any language) | Explains your **rights, options, next step** |
| A **voice note** 🎙️ | Understands the audio directly (ASR-free single pass), replies by **voice + text** |
| A **photo or PDF** 📄 of a notice/contract/order | Reads it and explains what it means and demands |
| **"Draft a reply / complaint / application…"** ✍️ | Produces a ready-to-send draft with fill-in placeholders |
| An **audio recording** 🔊 of a conversation | Pulls out the legally relevant points |

Commands in chat: `!help`, `!reset`.

## Requirements

- **Node.js 18+** (tested on 24)
- A **Google AI Studio API key** — free at https://aistudio.google.com/apikey
- A **phone with WhatsApp** to link the bot (you scan a QR once)
- `ffmpeg` is bundled via `ffmpeg-static` (no system install needed) for voice replies

## Setup

```bash
npm install
cp .env.example .env
# open .env and paste your key into GOOGLE_API_KEY
npm start
```

On first run a **QR code** prints in the terminal. On your phone:
**WhatsApp → Settings → Linked Devices → Link a Device**, and scan it.
The session is saved in `.wwebjs_auth/`, so you only scan once.

When you see `Nyayra is live and listening 🟢`, message the linked number from another
phone (or have a friend message it) and try:

- `My landlord gave me 15 days to leave. What are my rights?`
- Send a **photo** of any notice.
- Send a **voice note** describing a problem.
- `Draft a reply to a rejected insurance claim.`

## Configuration (`.env`)

| Var | Purpose | Default |
|---|---|---|
| `GOOGLE_API_KEY` | AI Studio key (**required**) | — |
| `MODEL_REASONING` / `MODEL_VERIFY` / `MODEL_DRAFT` / `MODEL_MULTIMODAL` | model per pipeline stage | `gemini-2.0-flash` |
| `MODEL_TTS` | voice-output model | `gemini-2.5-flash-preview-tts` |
| `TTS_VOICE` | prebuilt voice name | `Kore` |
| `VOICE_REPLIES` | send a voice note back for voice queries | `true` |
| `DEFAULT_LANGUAGE` | fallback reply language | user's language |
| `HISTORY_TURNS` | conversation memory per chat | `8` |

> **Gemma note:** the writeup's Gemma 4 roster isn't publicly available yet. Defaults use
> Gemini (multimodal, incl. native audio + PDF) so the whole pipeline runs today. Point any
> `MODEL_*` var at a Gemma model (e.g. `gemma-3-27b-it`) to move that stage onto Gemma —
> but Gemma on AI Studio is text/image only, so keep `MODEL_MULTIMODAL` on a model that
> accepts audio if you want the voice path.

## Architecture

```
WhatsApp (whatsapp-web.js)
        │  message: text / voice / image / pdf / audio
        ▼
   handler.js ── routes by type & intent
        ▼
   pipeline/nyayra.js
     mask PII ─▶ reason (council-style prompt) ─▶ verify vs. statute ─▶ unmask
        │
        └─ multimodal single pass for voice/image/pdf (no separate ASR stage)
        ▼
   llm/provider.js  ── single swappable backend (Google AI Studio today)
```

- **`src/pipeline/`** — the reasoning core: masking, prompts, orchestration, verifier, router.
- **`src/llm/provider.js`** — the only file that talks to the model API. Swap it to move to
  Ollama or a self-hosted Gemma without touching feature code.
- **`src/whatsapp/`** — client + message routing.
- **`src/features/`** — voice output (TTS → Ogg/Opus).

## Limitations & notes

- Reasoning quality is only as good as the model behind it; this is legal **understanding**,
  not legal advice, and the bot says so.
- PII masking is regex-based (fast, local) — a pragmatic stand-in for the full design's
  on-device model masking.
- Sessions are in-memory (single process). Use a store like Redis to scale or persist.
- Group chats and non-supported file types are ignored by design.
