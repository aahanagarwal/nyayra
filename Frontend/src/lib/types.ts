// Shared types for Nyayra frontend. Backend implements these shapes (see BACKEND_API.md).

export type LangCode = 'en' | 'hi' | 'ta' | 'bn';

export interface Language {
  code: LangCode;
  label: string;   // native label, e.g. "हिन्दी"
  english: string; // "Hindi"
}

export const LANGUAGES: Language[] = [
  { code: 'en', label: 'English', english: 'English' },
  { code: 'hi', label: 'हिन्दी', english: 'Hindi' },
  { code: 'ta', label: 'தமிழ்', english: 'Tamil' },
  { code: 'bn', label: 'বাংলা', english: 'Bengali' },
];

export type Mode = 'cloud' | 'local'; // local = offline, on-device

export type Role = 'user' | 'assistant';

// Structured legal answer: the three blocks from the spec.
export interface LegalAnswer {
  rights: string[];    // "What the law actually says applies to your situation."
  options: string[];   // "The realistic paths open to you, with their trade-offs."
  nextStep: string[];  // "A drafted reply, application, or checklist you can act on today."
  needsLawyer?: boolean; // no-advice-overreach flag
  lawyerNote?: string;
}

// One stage of the cascading Gemma council, for the collapsible trace.
export interface CouncilStage {
  id: string;
  label: string;   // "E2B · mask PII"
  role: string;    // short description
  status: 'done' | 'active' | 'pending';
  detail?: string;
}

export interface Attachment {
  id: string;
  name: string;
  kind: 'image' | 'pdf' | 'audio';
  sizeLabel: string;
}

export interface Message {
  id: string;
  role: Role;
  text?: string;              // plain text (user msg, or fallback)
  answer?: LegalAnswer;       // structured assistant answer
  council?: CouncilStage[];   // trace for assistant answers
  attachments?: Attachment[];
  lang?: LangCode;
  createdAt: number;
  pending?: boolean;
  thinkingMs?: number; // demo: how long the live council animation should run while pending
}

export interface Chat {
  id: string;
  title: string;
  updatedAt: number;
  messages: Message[];
}

export interface Draft {
  id: string;
  title: string;   // "Reply to eviction notice"
  kind: string;    // "Reply letter" | "Complaint" | "Application"
  updatedAt: number;
  preview: string;
}
