# Nyayra — Your Legal EA (frontend)

Claude-style chat UI for **Nyayra**, a Gemma-native multilingual legal companion.
**Frontend only** — no backend / no AI wired in yet. All server calls go through a
single stub seam (`src/lib/api.ts`) that returns typed placeholders. See
[`BACKEND_API.md`](./BACKEND_API.md) for the contract the backend agent implements.

## Run (Node.js 22)

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build to dist/
npm run preview  # serve the production build
```

## Demo mode (for screen recordings)

`DEMO_MODE = true` in `src/lib/api.ts` ships the app **pre-loaded with fake data**
so every feature shows on camera without a backend:
- 5 sample conversations in the sidebar (eviction, Hindi voice note, one-sided
  rental contract, insurance rejection with a "needs a lawyer" callout, offline
  police-complaint) — each with a full council trace.
- 4 sample drafts in the draft library.
- Typing a message returns a scripted, topic-matched answer after a short
  "deliberating…" pause. Try: *eviction*, *rental agreement*, *insurance claim*,
  *police complaint*.
- The **mic** button simulates an ASR-free Hindi voice note → Hindi answer.
- The **attach** button simulates parsing a document → one-sided-contract answer.
- Toggle **light/dark**, **cloud/local (offline)**, **voice replies**, and the
  **language** selector live.

Set `DEMO_MODE = false` to get the empty "backend not connected" shell.
When the backend is ready, it also overrides demo mode — see `BACKEND_API.md`.

### Scripted live demo (for recording)

Type an **exact trigger phrase** → a predetermined answer plays with a cinematic
"council deliberating" animation (stages light up one-by-one), then the
rights/options/next-step blocks reveal staggered. The full presenter runbook —
prompt order, narration lines, what shows on screen — is in
[`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md).

- Adjust deliberation time on the fly with a URL param: `?think=30` → ~30s per
  answer (e.g. `http://localhost:5173/?think=30`). Default per step is set in
  `DEMO_CONFIG.thinkingMs` / each `ScriptStep.thinkingMs` in `src/lib/demo.ts`.
- The **mic** button plays a scripted Hindi voice-note flow; **attach** plays a
  scripted document-parse flow — both animate the same way.
- Animations respect `prefers-reduced-motion`.

## What's built

- Claude-style layout: collapsible sidebar (history + draft library + language +
  offline toggle + settings), top bar (mode badge, voice-out, theme), centered
  chat thread, auto-growing composer.
- Structured legal answers rendered as three blocks — **Your rights · Your
  options · Your next step** — with a "needs a lawyer" callout.
- Collapsible **council trace** visualizing the Gemma cascade
  (E2B mask → router → 26B-A4B council → E4B verifier → 31B draft → E2B unmask).
- Multilingual UI (English · हिन्दी · தமிழ் · বাংলা), light/dark theme,
  cloud/local (offline) mode, voice + document attach (stubbed).

## Structure

```
src/
  App.tsx              app shell + state wiring
  lib/types.ts         shared types (the data contract)
  lib/api.ts           API SEAM — all backend calls, currently stubbed
  components/          Sidebar, TopBar, ChatView, MessageItem, CouncilTrace,
                       Composer, EmptyState, DraftLibrary
  styles/theme.css     brand tokens (light + dark)
```

## Going live

Implement the endpoints in `BACKEND_API.md`, replace the stub bodies in
`src/lib/api.ts` (signatures unchanged), and set `BACKEND_CONNECTED = true`.
No component changes needed.
