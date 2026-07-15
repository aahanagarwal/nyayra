import 'dotenv/config';

export const config = {
  googleApiKey: process.env.GOOGLE_API_KEY || '',
  models: {
    reasoning: process.env.MODEL_REASONING || 'gemma-4-26b-a4b-it',
    verify: process.env.MODEL_VERIFY || 'gemma-4-26b-a4b-it',
    draft: process.env.MODEL_DRAFT || 'gemma-4-31b-it',
    // Images/PDF: Gemma handles vision. Audio: Gemma can't, so voice notes and
    // recordings go through a Gemini flash model instead.
    multimodal: process.env.MODEL_MULTIMODAL || 'gemma-4-31b-it',
    audio: process.env.MODEL_AUDIO || 'gemini-2.5-flash',
    tts: process.env.MODEL_TTS || 'gemini-2.5-flash-preview-tts',
  },
  ttsVoice: process.env.TTS_VOICE || 'Kore',
  defaultLanguage: process.env.DEFAULT_LANGUAGE || "the user's language",
  // Off by default: Gemma has no TTS, and it saves an API call per voice note.
  voiceReplies: (process.env.VOICE_REPLIES || 'false').toLowerCase() === 'true',
  // The statute-verifier is a second reasoning pass. Off by default to halve
  // quota use per message; set ENABLE_VERIFIER=true to turn it back on.
  enableVerifier: (process.env.ENABLE_VERIFIER || 'false').toLowerCase() === 'true',
  historyTurns: parseInt(process.env.HISTORY_TURNS || '8', 10),
  authPath: process.env.WWEBJS_AUTH_PATH || '.wwebjs_auth',
};

export function assertConfig() {
  if (!config.googleApiKey) {
    throw new Error(
      'GOOGLE_API_KEY is not set. Copy .env.example to .env and add a key from https://aistudio.google.com/apikey'
    );
  }
}
