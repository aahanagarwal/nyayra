// Lightweight PII masking, run before text reaches the reasoning model, and
// reversed on the way out. This mirrors the writeup's "E2B mask/unmask" stage.
// It is regex-based (fast, local, deterministic) — not a substitute for the
// on-device model masking of the full design, but it keeps obvious identifiers
// out of the prompt and is restored verbatim in the reply.

const PATTERNS = [
  // Indian phone numbers (10 digits, optional +91)
  { tag: 'PHONE', re: /(?:\+?91[\-\s]?)?[6-9]\d{9}\b/g },
  // Aadhaar-like 12-digit (spaced or not)
  { tag: 'AADHAAR', re: /\b\d{4}\s?\d{4}\s?\d{4}\b/g },
  // PAN
  { tag: 'PAN', re: /\b[A-Z]{5}\d{4}[A-Z]\b/g },
  // Email
  { tag: 'EMAIL', re: /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g },
];

// Returns { masked, map }. map is used by unmask() to restore originals.
export function mask(text) {
  if (!text) return { masked: text, map: {} };
  let masked = text;
  const map = {};
  const counters = {};
  for (const { tag, re } of PATTERNS) {
    masked = masked.replace(re, (m) => {
      counters[tag] = (counters[tag] || 0) + 1;
      const token = `[[${tag}_${counters[tag]}]]`;
      map[token] = m;
      return token;
    });
  }
  return { masked, map };
}

export function unmask(text, map) {
  if (!text || !map) return text;
  let out = text;
  for (const [token, original] of Object.entries(map)) {
    out = out.split(token).join(original);
  }
  return out;
}
