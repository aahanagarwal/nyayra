import wweb from 'whatsapp-web.js';
import { config } from '../config.js';
import { log } from '../utils/logger.js';
import { addTurn, historyText, resetSession } from '../utils/session.js';
import {
  answerQuestion,
  answerVoice,
  parseDocument,
  analyzeRecording,
  draftDocument,
} from '../pipeline/nyayra.js';
import { synthesizeVoice } from '../features/voiceOut.js';

const { MessageMedia } = wweb;

const HELP = `🟢 *Nyayra — Your Legal EA*
Justice you can talk to. Send me any of these:

• *A question* — describe your situation in your own language (Hindi, Tamil, English…). I'll explain your rights, options, and next step.
• *A voice note* 🎙️ — ask by speaking; I reply by voice + text.
• *A photo or PDF* 📄 — of a notice, contract, or order. I'll read it and tell you what it means.
• *"Draft a…"* ✍️ — a reply, complaint, application, or legal notice.
• *An audio recording* 🔊 — of a conversation. I'll pull out the legally relevant points.

Commands: *!help*  ·  *!reset* (clear our chat memory)

_Nyayra gives legal understanding, not a substitute for a lawyer._`;

const ERR = 'Sorry — something went wrong on my side. Please try again in a moment.';
// Explicit "write me a document" requests. Matches English + common Hindi verbs.
const DRAFT_RE = /\b(draft|write|compose|prepare|likho|likh\s?do|banao|bana\s?do)\b.*\b(reply|response|letter|complaint|application|notice|petition|email|patra|shikayat|aavedan|jawab|notice)\b|^\s*(draft|write|likho)\b/i;
const MAX_MEDIA_BYTES = 18 * 1024 * 1024; // stay under the inline request limit

function mediaBytes(base64) {
  return Math.floor((base64.length * 3) / 4);
}

// Split long text so it doesn't hit WhatsApp's per-message limit.
function chunk(text, size = 4000) {
  if (text.length <= size) return [text];
  const parts = [];
  let rest = text;
  while (rest.length > size) {
    let cut = rest.lastIndexOf('\n', size);
    if (cut < size * 0.5) cut = size;
    parts.push(rest.slice(0, cut));
    rest = rest.slice(cut);
  }
  if (rest.trim()) parts.push(rest);
  return parts;
}

export function createHandler(client) {
  // Send via the client + chatId directly. Avoids getChat(), which throws on
  // some WhatsApp Web builds. Returns nothing; failures are logged, not thrown.
  const send = async (chatId, content, opts) => {
    try {
      await client.sendMessage(chatId, content, opts);
    } catch (e) {
      log.error('sendMessage failed:', e?.message);
    }
  };
  const sendText = async (chatId, text) => {
    for (const part of chunk(text)) await send(chatId, part);
  };
  // Typing indicator is best-effort; never let it break the flow.
  const setTyping = async (chatId) => {
    try {
      const chat = await client.getChatById(chatId);
      await chat.sendStateTyping();
    } catch {}
  };

  function remember(chatId, userText, botText) {
    addTurn(chatId, 'user', userText);
    addTurn(chatId, 'bot', botText);
  }

  async function deliverVoiceAnswer(chatId, text, userLabel) {
    await sendText(chatId, text);
    remember(chatId, userLabel, text);
    if (!config.voiceReplies) return;
    try {
      const ogg = await synthesizeVoice(text);
      const media = new MessageMedia('audio/ogg; codecs=opus', ogg.toString('base64'));
      await send(chatId, media, { sendAudioAsVoice: true });
    } catch (e) {
      log.warn('voice reply skipped (text already sent):', e?.message);
    }
  }

  return async function onMessage(msg) {
    const chatId = msg.from;
    // Ignore status broadcasts and group messages (front door is 1:1 for now).
    if (!chatId || chatId === 'status@broadcast' || chatId.endsWith('@g.us')) return;
    if (msg.fromMe) return;

    const body = (msg.body || '').trim();

    try {
      // ---- Commands ----
      if (/^[!/]help$/i.test(body)) {
        await send(chatId, HELP);
        return;
      }
      if (/^[!/]reset$/i.test(body)) {
        resetSession(chatId);
        await send(chatId, 'Cleared. We can start fresh. 🌱');
        return;
      }

      await setTyping(chatId);
      const history = historyText(chatId);

      // ---- Media messages ----
      if (msg.hasMedia) {
        const media = await msg.downloadMedia();
        if (!media?.data) {
          await send(chatId, "I couldn't open that attachment. Could you resend it?");
          return;
        }
        if (mediaBytes(media.data) > MAX_MEDIA_BYTES) {
          await send(chatId, 'That file is a bit large for me to process. Try a shorter clip or a single page.');
          return;
        }
        const payload = { mimeType: (media.mimetype || '').split(';')[0], data: media.data };
        const mime = payload.mimeType;

        // Voice note -> spoken legal query (ASR-free single pass)
        if (msg.type === 'ptt' || (msg.type === 'audio' && (msg.duration || 0) <= 60)) {
          const reply = await answerVoice(payload, { history });
          await deliverVoiceAnswer(chatId, reply, body || '(voice note)');
          return;
        }
        // Longer audio -> conversation/recording analysis
        if (msg.type === 'audio' || mime.startsWith('audio/')) {
          const reply = await analyzeRecording(payload, body, { history });
          await sendText(chatId, reply);
          remember(chatId, '(sent an audio recording)', reply);
          return;
        }
        // Image or PDF -> document parsing
        if (mime.startsWith('image/') || mime === 'application/pdf') {
          const reply = await parseDocument(payload, body, { history });
          await sendText(chatId, reply);
          remember(chatId, `(sent a document${body ? ': ' + body : ''})`, reply);
          return;
        }
        await send(chatId, "I can read photos, PDFs, voice notes, and audio recordings. That file type isn't supported yet.");
        return;
      }

      // ---- Plain text ----
      if (!body) return;

      // Cheap intent check (no API call): explicit drafting request -> drafter.
      if (DRAFT_RE.test(body)) {
        const reply = await draftDocument(body, { history });
        await sendText(chatId, reply);
        remember(chatId, body, reply);
        return;
      }
      // Everything else -> the rights/options/next-step answer path.
      const reply = await answerQuestion(body, { history });
      await sendText(chatId, reply);
      remember(chatId, body, reply);
    } catch (err) {
      log.error('handler error:', err?.message || err);
      await send(chatId, ERR);
    }
  };
}
