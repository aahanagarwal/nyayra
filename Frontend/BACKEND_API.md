# Nyayra — Backend API Specification

This document is the contract between the **frontend** (this repo) and the **backend
agent** who will implement the real Gemma cascade. The frontend already works
end-to-end against stubs; every stub lives in **`src/lib/api.ts`** and returns typed
placeholder data. To go live, implement the HTTP endpoints below and replace each
function body in `api.ts` with a `fetch` call — **do not change the function
signatures or the TypeScript return shapes**, which are defined in `src/lib/types.ts`.

Set `BACKEND_CONNECTED = true` in `src/lib/api.ts` once the endpoints are up.

---

## 0. Conventions

- Base URL: configurable via `VITE_API_BASE` env var (default `/api`).
- All request/response bodies are JSON unless noted (file upload is multipart).
- Auth: session token in `Authorization: Bearer <token>` header. (Anonymous
  sessions allowed for the WhatsApp-parity flow; app users may be authenticated.)
- All timestamps are epoch milliseconds (number).
- Language codes: `"en" | "hi" | "ta" | "bn"` (extendable). See `LangCode`.
- Mode: `"cloud" | "local"`. `local` means the on-device / offline path — the
  frontend still calls the same functions, but the backend/runtime is expected to
  run the E-model pipeline locally and transmit nothing off-device. The frontend
  passes `mode` on every message so the router can honour it.

### Core data shapes (mirror of `src/lib/types.ts`)

```ts
type LangCode = 'en' | 'hi' | 'ta' | 'bn';
type Mode = 'cloud' | 'local';
type Role = 'user' | 'assistant';

interface LegalAnswer {
  rights: string[];      // statute-grounded rights that apply
  options: string[];     // realistic paths + trade-offs
  nextStep: string[];    // concrete actions / drafted artifact pointers
  needsLawyer?: boolean; // no-advice-overreach flag
  lawyerNote?: string;   // shown when needsLawyer is true
}

interface CouncilStage {
  id: string;
  label: string;   // e.g. "E4B verifier"
  role: string;    // human-readable description of what this stage did
  status: 'done' | 'active' | 'pending';
  detail?: string; // optional per-stage note (e.g. which statute matched)
}

interface Attachment {
  id: string;
  name: string;
  kind: 'image' | 'pdf' | 'audio';
  sizeLabel: string;
}

interface Message {
  id: string;
  role: Role;
  text?: string;             // plain text (user turn, or plain assistant text)
  answer?: LegalAnswer;      // structured assistant answer (rights/options/next step)
  council?: CouncilStage[];  // trace of the cascade for this answer
  attachments?: Attachment[];
  lang?: LangCode;
  createdAt: number;
  pending?: boolean;         // frontend-only; backend never sets true
}

interface Chat  { id: string; title: string; updatedAt: number; messages: Message[]; }
interface Draft { id: string; title: string; kind: string; updatedAt: number; preview: string; }
```

---

## 1. Send a message — `POST /api/chat/message`

The primary endpoint. Runs the cascade (mask → router → council → verifier →
draft → unmask) and returns one assistant `Message`.

**Frontend fn:** `sendMessage(input: SendMessageInput): Promise<Message>`

Request body:
```json
{
  "chatId": "chat_ab12cd34 | null",   // null starts a new conversation
  "text": "landlord wants me out",
  "lang": "hi",
  "mode": "cloud",
  "attachmentIds": ["att_xy78"]        // ids returned by /document/parse or /upload
}
```

Response `200` — an assistant `Message`:
```json
{
  "id": "msg_9f2a",
  "role": "assistant",
  "answer": {
    "rights": ["Under the Rent Control Act ... you are entitled to ..."],
    "options": ["Negotiate: lower risk, ...", "Contest in court: ..."],
    "nextStep": ["We drafted a reply letter — see Drafts.", "Respond within 15 days."],
    "needsLawyer": false,
    "lawyerNote": ""
  },
  "council": [
    { "id": "s1", "label": "E2B · mask PII + HyDE", "role": "Stripped identifiers, rewrote query", "status": "done" },
    { "id": "s3", "label": "Council · 26B-A4B MoE", "role": "advocate · devil's advocate · bench · opposition", "status": "done" },
    { "id": "s4", "label": "E4B verifier", "role": "Every claim checked against statute text", "status": "done", "detail": "3 claims verified, 1 rejected" }
  ],
  "lang": "hi",
  "createdAt": 1750000000000
}
```

Notes for the backend:
- If `chatId` is `null`, create the chat server-side and include its id (the
  frontend currently generates a local chat id; align on server id if you persist —
  see §5). Minimum: return a valid assistant message.
- `council` should reflect the **actual** stages run for this query (text path vs
  audio path vs offline). Omit stages that did not run. `status` lets the UI show a
  live stepper if you stream (see below).
- `needsLawyer: true` when the matter exceeds "understanding" (e.g. active
  litigation, criminal exposure). The UI renders `lawyerNote` as a callout.

### Streaming (recommended, optional)

For chat-latency feel, stream Server-Sent Events instead of a single JSON body.
Suggested event types:
- `stage` → a `CouncilStage` with `status:"active"|"done"` as the cascade
  progresses (UI updates the trace live).
- `answer_delta` → partial `LegalAnswer` fields (append to arrays).
- `done` → final `Message`.

If you stream, keep the non-streaming JSON response available as a fallback and
document the `Accept: text/event-stream` toggle. The current frontend consumes the
non-streaming shape; wiring SSE is a small change in `api.ts`.

---

## 2. Voice in — `POST /api/voice/transcribe`

ASR-free on the model side, but the frontend still needs a text handle for the
transcript to render the user's turn.

**Frontend fn:** `transcribeVoice(blob: Blob, lang: LangCode): Promise<{ text: string }>`

Request: `multipart/form-data` — fields: `audio` (16 kHz wav/webm blob), `lang`.
Response `200`:
```json
{ "text": "मेरा मकान मालिक मुझे निकालना चाहता है" }
```
If the product feeds audio tokens straight into the reasoning model (no separate
transcript), still return a best-effort transcript string here for display, or an
empty string `""` if none is produced. In that case the audio should be sent to
`/chat/message` as an attachment of kind `audio`.

---

## 3. Voice out — `POST /api/voice/synthesize`

**Frontend fn:** `synthesizeSpeech(text: string, lang: LangCode): Promise<{ audioUrl: string | null }>`

Request:
```json
{ "text": "आपके पास 15 दिन हैं ...", "lang": "hi" }
```
Response `200`:
```json
{ "audioUrl": "https://cdn.nyayra.app/tts/abc.mp3" }
```
Return `{ "audioUrl": null }` if voice-out is unavailable. Triggered only when the
user has the voice-out toggle on (top bar).

---

## 4. Parse a document — `POST /api/document/parse`

Handles the "photo/PDF of a notice" flow.

**Frontend fn:** `parseDocument(file: File): Promise<{ summary: string | null }>`

Request: `multipart/form-data` — field `file` (image/* or application/pdf).
Response `200`:
```json
{
  "id": "att_xy78",
  "summary": "This is an eviction notice dated ... demanding vacation within 15 days under ...",
  "kind": "pdf"
}
```
- `id` is the attachment handle to pass back in `sendMessage.attachmentIds`.
- `summary` is a plain-language description shown to the user; `null` if parsing
  failed. The heavy reasoning happens later in `/chat/message`; this endpoint just
  extracts + describes.
- Enforce PII masking here too — the on-device E2B stage must run before the
  document leaves the device in `local` mode.

---

## 5. Conversations — `GET /api/chats`, `GET /api/chats/:id`, `DELETE /api/chats/:id`

**Frontend fn:** `listChats(): Promise<Chat[]>` (loads the sidebar history).

`GET /api/chats` response `200`: array of `Chat` **without** full message bodies is
acceptable for the list (title + id + updatedAt); the frontend only needs
`id`, `title`, `updatedAt` for the sidebar, and `messages` when a chat is opened.

Recommended split:
- `GET /api/chats` → `[{ id, title, updatedAt }]` (messages may be `[]`).
- `GET /api/chats/:id` → full `Chat` with `messages`.
- `DELETE /api/chats/:id` → `204`.
- `PATCH /api/chats/:id` `{ "title": "..." }` → rename (optional).

> Frontend TODO when backend lands: `App.tsx` currently keeps chats in local state
> and generates chat ids client-side. Point `onSelectChat` at `GET /api/chats/:id`
> to hydrate messages, and adopt server-issued chat ids from `sendMessage`.

---

## 6. Drafts — `GET /api/drafts`, `GET /api/drafts/:id`

**Frontend fn:** `getDrafts(): Promise<Draft[]>` (populates the sidebar "Drafts" list).

`GET /api/drafts` response `200`:
```json
[
  { "id": "draft_1", "title": "Reply to eviction notice", "kind": "Reply letter",
    "updatedAt": 1750000000000, "preview": "To the landlord, ... I am writing in response ..." }
]
```
`GET /api/drafts/:id` → full draft body (markdown/plain text) for viewing/exporting.
Drafts are produced by the 31B sandbox stage; when a `sendMessage` answer creates a
drafted artifact, also persist it as a Draft and reference it from
`answer.nextStep` (e.g. "We drafted a reply — open it in Drafts").

---

## 7. Languages & config — `GET /api/config` (optional)

If the supported-language set should be server-driven rather than the hardcoded
`LANGUAGES` array in `types.ts`:
```json
{
  "languages": [{ "code": "hi", "label": "हिन्दी", "english": "Hindi" }],
  "modes": ["cloud", "local"],
  "features": { "voiceIn": true, "voiceOut": true, "documentParse": true }
}
```
Frontend can gate mic / attach / voice-out buttons on `features`.

---

## 8. Errors

Return standard HTTP status codes with a JSON body:
```json
{ "error": { "code": "rate_limited", "message": "Too many requests, retry in 30s." } }
```
The frontend surfaces failures inline in the chat ("Could not reach Nyayra …") and
should show `error.message` when present. Recommended codes: `unauthorized`,
`rate_limited`, `unsupported_language`, `document_unreadable`, `internal`.

---

## 9. Privacy expectations (architectural, not optional)

Per the product brief, the backend must honour:
- **PII masking before reasoning.** Names/numbers/identifiers stripped by the E2B
  stage before any larger model sees the query; restored only at unmask. The
  council must never receive raw identity.
- **`local` mode = on-device.** When `mode === "local"`, nothing leaves the device:
  the whole pipeline (mask, reason, draft, unmask) runs on the local E-model. The
  frontend already flags this in the UI; the runtime must enforce it.
- **Statute-grounded output.** The E4B verifier rejects unsupported claims; only
  verified claims appear in `LegalAnswer`. Prefer returning fewer, verified rights
  over confident-but-unsupported ones.
- **No advice overreach.** Set `needsLawyer` + `lawyerNote` rather than
  overstepping into representation.

---

## 10. Endpoint ↔ frontend function map (quick reference)

| Frontend fn (`src/lib/api.ts`) | Method & path | Purpose |
| --- | --- | --- |
| `sendMessage` | `POST /api/chat/message` | Run the cascade, return an answer |
| `transcribeVoice` | `POST /api/voice/transcribe` | Voice in → transcript |
| `synthesizeSpeech` | `POST /api/voice/synthesize` | Text → voice out |
| `parseDocument` | `POST /api/document/parse` | Photo/PDF → summary + attachment id |
| `listChats` | `GET /api/chats` | Sidebar history |
| (open chat) | `GET /api/chats/:id` | Hydrate a conversation |
| `getDrafts` | `GET /api/drafts` | Sidebar draft library |
| (view draft) | `GET /api/drafts/:id` | Full draft body |
| (config) | `GET /api/config` | Languages / feature flags |

Implement these, flip `BACKEND_CONNECTED` to `true`, and the existing UI lights up
with no component changes.
