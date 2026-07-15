// Browser-native text-to-speech for the demo (Web Speech API — no dependency,
// no backend). Used to "speak" a reply back when the user talks via the mic,
// or whenever the voice-out toggle is on. If the OS has no matching voice it
// falls back to the default voice; if the API is missing it silently no-ops.

import type { LangCode, LegalAnswer } from './types';

const BCP47: Record<LangCode, string> = {
  en: 'en-IN',
  hi: 'hi-IN',
  ta: 'ta-IN',
  bn: 'bn-IN',
};

function pickVoice(lang: LangCode): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return undefined;
  const want = lang; // 2-letter
  return (
    voices.find((v) => v.lang?.toLowerCase() === BCP47[lang].toLowerCase()) ??
    voices.find((v) => v.lang?.toLowerCase().startsWith(want)) ??
    undefined
  );
}

export function isTtsAvailable(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

export function speak(text: string, lang: LangCode): void {
  if (!isTtsAvailable() || !text.trim()) return;
  try {
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = BCP47[lang];
    utter.rate = 1;
    utter.pitch = 1;
    const v = pickVoice(lang);
    if (v) utter.voice = v;
    // Voices can load asynchronously; if none yet, retry once after they load.
    if (!v && window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.addEventListener(
        'voiceschanged',
        () => {
          const v2 = pickVoice(lang);
          if (v2) utter.voice = v2;
          window.speechSynthesis.speak(utter);
        },
        { once: true },
      );
      return;
    }
    window.speechSynthesis.speak(utter);
  } catch {
    /* ignore — TTS is a nicety, never block the UI */
  }
}

export function stopSpeaking(): void {
  if (!isTtsAvailable()) return;
  try {
    window.speechSynthesis.cancel();
  } catch {
    /* ignore */
  }
}

// A concise spoken version of a structured answer (reading every bullet aloud
// would be too long). Speaks the lead right, option, and next step.
export function spokenSummary(a: LegalAnswer): string {
  return [a.rights[0], a.options[0], a.nextStep[0]].filter(Boolean).join(' ');
}
