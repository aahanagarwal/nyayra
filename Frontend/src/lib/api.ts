// ---------------------------------------------------------------------------
// API SEAM. Frontend talks ONLY to these functions. All are placeholder stubs
// today (no backend). The backend agent replaces the bodies with real calls;
// signatures and return shapes are the contract (see BACKEND_API.md).
// ---------------------------------------------------------------------------

import type { Chat, Draft, LangCode, LegalAnswer, Message, Mode } from './types';
import {
  DEMO_CHATS,
  DEMO_DRAFTS,
  DEMO_DOC_SUMMARY,
  DEMO_VOICE_TRANSCRIPT,
  answerFor,
  docReply,
  voiceReply,
} from './demo';

// Toggle: when true, every call returns a "backend not connected" placeholder.
export const BACKEND_CONNECTED = false;

// Demo mode: when true, the app is fully populated with realistic FAKE data so
// every feature can be shown on camera without a backend. Set to false to get
// the empty "backend not connected" shell instead.
export const DEMO_MODE = true;

function uid(prefix = 'id'): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

const PLACEHOLDER_ANSWER: LegalAnswer = {
  rights: ['Backend not connected — statute-grounded rights will appear here.'],
  options: ['Backend not connected — realistic options with trade-offs will appear here.'],
  nextStep: ['Backend not connected — a drafted reply / application / checklist will appear here.'],
  needsLawyer: false,
};

export interface SendMessageInput {
  chatId: string | null;
  text: string;
  lang: LangCode;
  mode: Mode;
  attachmentIds?: string[];
}

// Special hint the frontend can pass to force a scripted demo flow.
export type DemoFlow = 'voice' | 'document' | undefined;

// POST /api/chat/message  (streaming in real impl)
export async function sendMessage(input: SendMessageInput, flow?: DemoFlow): Promise<Message> {
  if (DEMO_MODE) {
    await delay(1100); // let the "deliberating…" state show
    const { answer, council } =
      flow === 'voice' ? voiceReply()
      : flow === 'document' ? docReply()
      : answerFor(input.text, input.lang);
    return {
      id: uid('msg'),
      role: 'assistant',
      answer,
      council,
      lang: input.lang,
      createdAt: Date.now(),
    };
  }
  if (!BACKEND_CONNECTED) {
    return {
      id: uid('msg'),
      role: 'assistant',
      answer: PLACEHOLDER_ANSWER,
      council: defaultCouncilTrace(),
      lang: input.lang,
      createdAt: Date.now(),
    };
  }
  throw new Error('Not implemented — see BACKEND_API.md');
}

// POST /api/voice/transcribe  (audio in → text). ASR-free on the model side.
export async function transcribeVoice(_blob: Blob, _lang: LangCode): Promise<{ text: string }> {
  if (DEMO_MODE) {
    await delay(900);
    return { text: DEMO_VOICE_TRANSCRIPT };
  }
  return { text: '' }; // placeholder: backend not connected
}

// POST /api/voice/synthesize  (text → audio url)
export async function synthesizeSpeech(_text: string, _lang: LangCode): Promise<{ audioUrl: string | null }> {
  return { audioUrl: null };
}

// POST /api/document/parse  (image/pdf → extracted meaning)
export async function parseDocument(_file: File): Promise<{ summary: string | null }> {
  if (DEMO_MODE) {
    await delay(800);
    return { summary: DEMO_DOC_SUMMARY };
  }
  return { summary: null };
}

// GET /api/chats
export async function listChats(): Promise<Chat[]> {
  if (DEMO_MODE) return DEMO_CHATS;
  return [];
}

// GET /api/drafts
export async function getDrafts(): Promise<Draft[]> {
  if (DEMO_MODE) return DEMO_DRAFTS;
  return [];
}

// Static, illustrative council trace shown in the collapsible "how this answer
// was reached" block. Mirrors the pipeline in the spec (section 5).
export function defaultCouncilTrace() {
  return [
    { id: 's1', label: 'E2B · mask PII + HyDE', role: 'Strip names & IDs, rewrite query with statutory context', status: 'done' as const },
    { id: 's2', label: 'Router', role: 'Complexity → path (cloud or offline)', status: 'done' as const },
    { id: 's3', label: 'Council · 26B-A4B MoE', role: 'advocate · devil’s advocate · bench · opposition', status: 'done' as const },
    { id: 's4', label: 'E4B verifier', role: 'Every claim checked against statute text', status: 'done' as const },
    { id: 's5', label: '31B sandbox', role: 'Artifact / draft generation', status: 'done' as const },
    { id: 's6', label: 'E2B · unmask', role: 'Restore identifiers, return rights · options · next step', status: 'done' as const },
  ];
}

export { uid };
