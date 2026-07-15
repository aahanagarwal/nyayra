import { generate } from '../llm/provider.js';
import { config } from '../config.js';
import { mask, unmask } from './mask.js';
import {
  ANSWER_SYSTEM,
  DOCUMENT_SYSTEM,
  DRAFT_SYSTEM,
  RECORDING_SYSTEM,
  VOICE_STYLE,
} from './prompts.js';
import { log } from '../utils/logger.js';

// The Nyayra pipeline. A pragmatic, runnable realisation of the writeup's
// cascade: mask PII -> reason (council-style, baked into one strong prompt)
// -> lightweight statute verifier pass -> unmask. The role-per-model routing
// from the design maps here to role-per-prompt so it runs on one API today;
// swap models per stage via config.models to reintroduce true multi-model routing.

function withHistory(parts, history) {
  if (history) parts.unshift({ text: `Recent conversation so far:\n${history}\n---\n` });
  return parts;
}

// Verifier pass: re-read the drafted answer and strip/flag unsupported legal
// claims. Cheap insurance against confident-but-wrong statute citations.
async function verify(answer, question) {
  const system = `You are a strict legal verifier. You are given a user's situation and a draft answer from a legal assistant. Your job: catch any specific legal claim (statute/section numbers, named acts, case names, hard deadlines, guaranteed outcomes) that is stated with more confidence than is warranted or looks fabricated.
Return the answer rewritten so that:
- Any statute/section number or case name you are not confident is real is softened to a general description (e.g. "the relevant tenancy law") rather than a possibly-wrong citation.
- Guarantees of outcome become realistic likelihoods.
- Everything else is preserved, including language, structure, and tone.
Output ONLY the corrected answer, nothing else.`;
  try {
    return await generate({
      model: config.models.verify,
      system,
      parts: [{ text: `USER SITUATION:\n${question}\n\nDRAFT ANSWER:\n${answer}` }],
      temperature: 0.1,
    });
  } catch (e) {
    log.warn('verifier skipped:', e?.message);
    return answer; // fail open — a slightly less-verified answer beats no answer
  }
}

// Answer a text question / described situation.
export async function answerQuestion(question, { history, forVoice = false } = {}) {
  const { masked, map } = mask(question);
  const system = ANSWER_SYSTEM + (forVoice ? VOICE_STYLE : '');
  const parts = withHistory([{ text: masked }], history);
  const raw = await generate({ model: config.models.reasoning, system, parts, temperature: 0.4 });
  const verified = !forVoice && config.enableVerifier ? await verify(raw, masked) : raw;
  return unmask(verified, map);
}

// Parse a document (image or PDF). media = { mimeType, data(base64) }.
export async function parseDocument(media, caption, { history } = {}) {
  const { masked, map } = mask(caption || '');
  const parts = withHistory(
    [
      { text: masked ? `The user says: ${masked}` : 'The user sent this document with no caption.' },
      { media },
    ],
    history
  );
  const raw = await generate({
    model: config.models.multimodal,
    system: DOCUMENT_SYSTEM,
    parts,
    temperature: 0.3,
  });
  return unmask(raw, map);
}

// Answer a voice query. audio = { mimeType, data(base64) }. Single multimodal
// pass — audio goes straight into the model (the writeup's ASR-free path).
export async function answerVoice(audio, { history } = {}) {
  const parts = withHistory(
    [{ text: 'The user asked the following as a voice note. Understand it and help.' }, { media: audio }],
    history
  );
  return generate({
    model: config.models.audio,
    system: ANSWER_SYSTEM + VOICE_STYLE,
    parts,
    temperature: 0.4,
  });
}

// Analyse a recorded conversation. audio = { mimeType, data(base64) }.
export async function analyzeRecording(audio, caption, { history } = {}) {
  const parts = withHistory(
    [
      { text: caption ? `Context from the user: ${caption}` : 'Analyse this recorded conversation.' },
      { media: audio },
    ],
    history
  );
  return generate({
    model: config.models.audio,
    system: RECORDING_SYSTEM,
    parts,
    temperature: 0.3,
  });
}

// Draft a legal document.
export async function draftDocument(request, { history } = {}) {
  const { masked, map } = mask(request);
  const parts = withHistory([{ text: masked }], history);
  const raw = await generate({
    model: config.models.draft,
    system: DRAFT_SYSTEM,
    parts,
    temperature: 0.5,
  });
  return unmask(raw, map);
}
