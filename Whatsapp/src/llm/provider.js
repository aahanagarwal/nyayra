import { GoogleGenAI } from '@google/genai';
import { config } from '../config.js';
import { log } from '../utils/logger.js';

// Single place that talks to the model backend. Swap this file to move off
// Google AI Studio (e.g. to Ollama or a self-hosted Gemma) without touching
// the pipeline or feature code.

let client;
function ai() {
  if (!client) client = new GoogleGenAI({ apiKey: config.googleApiKey });
  return client;
}

const isGemma = (model) => /gemma/i.test(model);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Each model has its own quota bucket, so when one is rate-limited we roll over
// to a smaller sibling instead of failing. Order = try first → last.
const FALLBACKS = {
  // Gemma 4 roster (the writeup's models), each falling back to its sibling.
  'gemma-4-26b-a4b-it': ['gemma-4-26b-a4b-it', 'gemma-4-31b-it'],
  'gemma-4-31b-it': ['gemma-4-31b-it', 'gemma-4-26b-a4b-it'],
  // Gemini flash family for the audio path.
  'gemini-2.5-flash': ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash-lite'],
  'gemini-2.0-flash': ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-2.5-flash-lite'],
};
const chainFor = (model) => FALLBACKS[model] || [model];

function is429(err) {
  const m = String(err?.message || err);
  return err?.status === 429 || /429|RESOURCE_EXHAUSTED|Too Many Requests/i.test(m);
}

// Pull the server-suggested retry delay (seconds) out of the error, if any.
function retryDelayMs(err) {
  const m = String(err?.message || err).match(/retryDelay"?:\s*"?(\d+(?:\.\d+)?)s/i);
  return m ? Math.ceil(parseFloat(m[1]) * 1000) : 0;
}

/**
 * Generate text from a model, with automatic fallback across sibling models on
 * rate limits and a single short backoff retry if the whole chain is limited.
 * @param {object} o
 * @param {string} o.model            primary model id (fallbacks derived from it)
 * @param {string} [o.system]         system instruction
 * @param {Array}  o.parts            { text } or { media: { mimeType, data(base64) } }
 * @param {number} [o.temperature]
 * @param {boolean} [o.json]          request JSON output (ignored for Gemma)
 * @returns {Promise<string>}
 */
export async function generate({ model, system, parts, temperature = 0.4, json = false }) {
  const chain = chainFor(model);
  const MAX_BACKOFF_MS = 12_000; // don't leave a WhatsApp user hanging forever

  let lastErr;
  for (let pass = 0; pass < 2; pass++) {
    for (const m of chain) {
      const contentParts = parts.map((p) =>
        p.media ? { inlineData: { mimeType: p.media.mimeType, data: p.media.data } } : { text: p.text }
      );
      const cfg = { temperature };
      if (isGemma(m)) {
        if (system) contentParts.unshift({ text: `${system}\n\n---\n` });
      } else {
        if (system) cfg.systemInstruction = system;
        if (json) cfg.responseMimeType = 'application/json';
      }

      try {
        const res = await ai().models.generateContent({
          model: m,
          contents: [{ role: 'user', parts: contentParts }],
          config: cfg,
        });
        if (m !== model) log.step('fell back to', m);
        return (res.text || '').trim();
      } catch (err) {
        lastErr = err;
        if (!is429(err)) {
          log.error(`generate(${m}) failed:`, err?.message || err);
          throw err;
        }
        log.warn(`rate-limited on ${m}${chain.indexOf(m) < chain.length - 1 ? ', trying next model' : ''}`);
      }
    }
    // Whole chain rate-limited. Back off briefly once, then retry the chain.
    if (pass === 0) {
      const wait = Math.min(retryDelayMs(lastErr) || 3000, MAX_BACKOFF_MS);
      log.warn(`all models rate-limited; backing off ${Math.round(wait / 1000)}s`);
      await sleep(wait);
    }
  }
  throw lastErr;
}

/**
 * Text-to-speech. Returns raw 24kHz 16-bit mono PCM as a Buffer.
 */
export async function tts(text, { voice = config.ttsVoice } = {}) {
  const res = await ai().models.generateContent({
    model: config.models.tts,
    contents: [{ role: 'user', parts: [{ text }] }],
    config: {
      responseModalities: ['AUDIO'],
      speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } } },
    },
  });
  const data = res.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
  if (!data) throw new Error('TTS returned no audio');
  return Buffer.from(data, 'base64');
}
