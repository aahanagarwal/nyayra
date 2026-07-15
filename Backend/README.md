# Nyayra backend

FastAPI + SQLite (aiosqlite/SQLAlchemy async) backend for Nyayra: a multilingual
legal-help assistant. A "council" of role-prompted Gemini calls (advocate,
opposition, and — for complex cases — a devil's advocate and a bench) debates
a user's question, every claim is checked against verbatim statute text before
it reaches the user, and PII is masked before it ever leaves the process and
unmasked only after verification.

## Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set GEMINI_API_KEYS to a comma-separated key list
# (durable keys look like AIza...; AQ.* ones are short-lived ephemeral tokens)
```

## Run

```bash
uvicorn app.main:app --reload
```

Or `python -m app.main` (same thing, via the `if __name__ == "__main__"` block).

On startup the app creates DB tables if they don't exist, ensures
`STORAGE_PATH` exists, builds a `KeyPool` + `GeminiClient`, and logs the
per-stage model roster. On shutdown it closes the `GeminiClient`'s HTTP
connection pool.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/api/chat/message` | body `{chatId\|null, text, lang, mode, attachmentIds[]}` -> `Message`. With `Accept: text/event-stream` -> SSE (`stage`, `answer_delta`, `done`, `error` events). The new/returned chat id comes back on the `X-Chat-Id` response header. |
| POST | `/api/voice/transcribe` | multipart `{audio, lang}` -> `{text}` |
| POST | `/api/voice/synthesize` | `{text, lang}` -> `{audioUrl: string\|null}` |
| POST | `/api/document/parse` | multipart `{file}` -> `{id, summary, kind}` |
| GET | `/api/files/{id}` | fetch a stored upload/generated file by id |
| GET | `/api/chats` | -> `[{id, title, updatedAt}]` (`messages` is `[]` in the list view) |
| GET | `/api/chats/{id}` | -> full `Chat` with `messages` |
| PATCH | `/api/chats/{id}` | `{title}` -> `Chat` |
| DELETE | `/api/chats/{id}` | -> 204 (soft delete) |
| GET | `/api/drafts` | -> `[Draft]` (`preview` truncated to 200 chars) |
| GET | `/api/drafts/{id}` | -> full `Draft` (`preview` holds the full draft body — the wire schema has no separate body field) |
| GET | `/api/config` | -> `{languages, modes, features}` |
| POST | `/api/whatsapp/webhook/inbound` | Twilio inbound message webhook (form-encoded) |
| POST | `/api/whatsapp/webhook/status` | Twilio delivery-status webhook |
| GET | `/api/system/health` | -> `{"status": "ok"}` |
| GET | `/api/system/models` | -> per-stage model roster + key pool stats |

Errors are always `{"error": {"code", "message"}}`, with `code` one of
`unauthorized`, `rate_limited`, `unsupported_language`, `document_unreadable`,
`internal`.

## Per-stage model config

Each pipeline stage's model is its own env var, read via
`Settings.model_for(stage)`:

| Stage | Env var | Default |
|---|---|---|
| PREP | `MODEL_PREP` | `gemini-2.5-flash` |
| ACT_SELECT | `MODEL_ACT_SELECT` | `gemini-2.5-flash` |
| COUNCIL | `MODEL_COUNCIL` | `gemini-2.5-flash` |
| VERIFY | `MODEL_VERIFY` | `gemini-2.5-flash` |
| DRAFT | `MODEL_DRAFT` | `gemini-2.5-flash` |
| UNMASK | `MODEL_UNMASK` | `gemini-2.5-flash` |

Plus two fixed-purpose models that aren't per-stage overrides:
`MODEL_AUDIO` (`gemini-2.5-flash-native-audio-latest`) and `MODEL_EMBED`
(`gemini-embedding-001`).

**To flip council to Gemma:** set `MODEL_COUNCIL=gemma-4-26b-a4b-it` in
`.env` and restart. Nothing else needs to change — `GeminiClient` already
omits `thinkingConfig.thinkingBudget` for any model name starting with
`"gemma"` (Gemma returns HTTP 400 if it's present at all), and JSON-schema
mode / `systemInstruction` / image input all work unmodified on both model
families.

## Honesty section

- **Which Gemma models actually exist:** only `gemma-4-26b-a4b-it` and
  `gemma-4-31b-it`. There is no E2B/E4B/12B Gemma variant in this project —
  don't configure one, it doesn't exist.
- **Gemma thinking is uncappable.** Unlike Gemini flash (`thinkingBudget: 0`
  forces near-instant, ~1.6s responses), Gemma has no way to disable its
  internal reasoning pass, so a single Gemma call runs 13–39s. That's why
  every stage defaults to Flash — Gemma is an opt-in trade of latency for
  (arguably) a different model's judgment on the council stage, not a
  drop-in faster/cheaper option.
- **No context caching on Gemma.** Every call re-sends the full prompt;
  there's no equivalent of Gemini's implicit/explicit context cache.
- **`mode: "local"` is accepted but runs cloud.** The frontend contract's
  `Mode` type includes `'local'`, and the API accepts it without error, but
  there is no on-device model in this codebase — a `local` request is
  served by the exact same cloud `GeminiClient` a `cloud` request would use.
