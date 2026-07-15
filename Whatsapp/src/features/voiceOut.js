import { tts } from '../llm/provider.js';
import { pcmToWav, wavToOggOpus } from '../utils/audio.js';

// Turn text into an Ogg/Opus buffer ready to send as a WhatsApp voice note.
// Returns null if synthesis fails, so callers can fall back to text.
export async function synthesizeVoice(text) {
  const pcm = await tts(text);
  const wav = pcmToWav(pcm);
  return wavToOggOpus(wav);
}
