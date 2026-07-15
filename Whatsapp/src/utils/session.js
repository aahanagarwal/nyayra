import { config } from '../config.js';

// In-memory per-chat state: recent turns + a pending draft context.
// Fine for a single-process bot / demo. Swap for Redis to scale.
const sessions = new Map();

export function getSession(chatId) {
  if (!sessions.has(chatId)) {
    sessions.set(chatId, { history: [], language: null, lastSituation: null });
  }
  return sessions.get(chatId);
}

export function addTurn(chatId, role, text) {
  const s = getSession(chatId);
  s.history.push({ role, text });
  const max = config.historyTurns * 2;
  if (s.history.length > max) s.history.splice(0, s.history.length - max);
}

// Render recent history as a compact transcript for prompt context.
export function historyText(chatId) {
  const s = getSession(chatId);
  if (!s.history.length) return '';
  return s.history.map((t) => `${t.role === 'user' ? 'User' : 'Nyayra'}: ${t.text}`).join('\n');
}

export function resetSession(chatId) {
  sessions.delete(chatId);
}
