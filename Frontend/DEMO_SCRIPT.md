# Nyayra — Live Demo Runbook

This is a **scripted demo**: every answer, council trace, and draft is fake data from
`src/lib/demo.ts`. There is no backend, no real model call, and no real legal advice —
the "council" animation is a timed UI sequence, not a live inference.

---

## Before you record

1. Run `npm run dev` and open **http://localhost:5173**.
2. Click **New chat** so the sidebar/history is fresh and the transcript starts empty.
3. Pick light or dark mode (top-right toggle) — whichever suits the recording.
4. (Optional) Set a longer thinking/deliberation duration so you have time to narrate —
   see below.
5. Do a silent dry run of the trigger phrases once before you hit record, so you don't
   fumble the exact wording on camera.

---

## Adjusting the thinking/loading duration

There are two ways to control how long the council "deliberates" before an answer appears:

1. **URL param (fastest, no code change):** append `?think=<seconds>` to the URL, e.g.

   ```
   http://localhost:5173/?think=30
   ```

   gives you roughly 30 seconds of deliberation per answer — plenty of time to talk over
   the council trace before the reveal.

2. **Edit the default in code:** change `DEMO_CONFIG.thinkingMs` in `src/lib/demo.ts`
   (and/or wherever it's consumed in `src/lib/api.ts`) to a new default in milliseconds.

Note that each step in `DEMO_SCRIPT` (in `src/lib/demo.ts`) also carries its **own**
`thinkingMs` value, so individual answers can be tuned to run longer or shorter than the
global default even without a URL override.

---

## The run order

Type the trigger text **exactly** as shown (matching is case-insensitive and tolerant of
extra trailing text) into the chat box, or trigger the mic/attach steps as noted.

| # | Action | Trigger | What happens on screen | Narration |
|---|--------|---------|-------------------------|-----------|
| 1 | Type | `landlord served me an eviction notice` | Full text-path council lights up stage by stage — mask+HyDE → router → advocate → devil's advocate → opposition+bench → verifier → draft → unmask — then rights/options/next-step slide in staggered. | "Watch the full council deliberate — masking, routing, debate, verification, drafting, unmasking." |
| 2 | Type | `draft a reply to the landlord` | Shorter, draft-focused council (router → sandbox draft → verifier); answer's next-step points to a saved letter in Drafts. | "Now it drafts the actual reply letter and saves it straight to Drafts." |
| 3 | Mic | Click the mic icon — plays a Hindi voice note (`voice-note.m4a`) — **no file needed, it's faked** | Audio-native pipeline: a single unified 12B stage understands the spoken Hindi directly (no ASR step). **The reply is then read back aloud in Hindi** via the browser's speech engine. | "Same question, spoken in Hindi — the 12B model understands the audio directly, no transcription step — and answers back by voice." |
| 4 | Attach | Click the paperclip — attaches `rental-agreement.pdf` | Document pipeline: mask+HyDE → **document parse** (clauses extracted, flagged) → router → advocate/opposition → verifier → unmask. | "Upload a contract and the council parses clauses, flagging the ones that are one-sided." |
| 5 | Type | `my insurance claim was rejected` | Full text-path council; verifier stage shows "4 claims verified · 1 unsupported claim rejected"; answer surfaces a **needs-a-lawyer** note. | "This one flags that a lawyer is genuinely worth it — the app knows when to say so." |
| 6 | Type | `i got a police notice under 41a` | Toggle to **Local/offline mode** first. Only two stages appear — everything runs on the on-device E2B model, no network call. | "Flip to offline mode — the whole answer runs on-device, nothing leaves the phone." |
| 7 | Type | `mujhe police notice mila hai 41a ke under` | Same offline pipeline, Hindi answer. | "Same offline path, this time answered in Hindi." |

---

## Other things to show on camera

- **Light/dark toggle** — top-right of the header.
- **Cloud/Local offline mode** — sidebar footer toggle; the badge flips and the copy
  changes to "nothing leaves this phone." **In offline mode every answer changes:** the
  trace collapses to a short 3-stage on-device pipeline, the reply is noticeably
  **shorter**, and it comes back **faster** (~45% of the cloud thinking time). Toggle it
  on, re-ask any trigger, and contrast it with the fuller cloud answer for a strong
  privacy/on-device beat.
- **Spoken replies (voice-out)** — the **mic** step automatically reads its answer aloud
  using the browser's built-in speech (Hindi). You can also toggle the **speaker icon**
  (top-right) on to have *every* reply spoken. Note: this uses your device/OS voices, so
  make sure a Hindi (hi-IN) voice is installed for the mic step to sound right — on
  Windows/macOS/Android these are usually available; otherwise it falls back to the
  default voice. Unmute your screen-recorder's system audio to capture it.
- **Council trace** — click to expand the collapsible trace under any assistant answer
  and scroll through the stages after they've finished animating.
- **Language switch** — change the active language from the sidebar and show a
  same-topic answer respond in the new language.
- **Draft library** — open the Drafts panel and click into a couple of saved items
  (e.g. "Reply to eviction notice", "Complaint to Insurance Ombudsman").
- **Sidebar collapse** — collapse/expand the sidebar to show the cleaner focused layout.

---

## Tips

- Type the trigger phrases **exactly** as listed — matching is case-insensitive and
  forgiving of extra trailing text, but the core phrase needs to be there.
- Let the council animation finish before talking over the reveal — the rights/options/
  next-step blocks stagger in right after the last stage completes.
- Use `?think=<seconds>` on the URL to buy yourself narration time without editing code.
