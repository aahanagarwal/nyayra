"""Deterministic PII masking for Indian personal data.

Regex-based, not model-based: a model that hallucinates or misses a span
would leak PII, so phone/Aadhaar/PAN/email are matched with plain regexes.
Person names are the one category regex cannot find; the caller (the PREP
stage) supplies model-detected name strings and mask() folds them in
alongside the regex categories using the same placeholder scheme.

Rupee amounts are intentionally NOT masked (not classified as PII here).
"""

from __future__ import annotations

import re

_PHONE_RE = re.compile(r"(?:\+91[-\s]?)?\b[6-9]\d{4}[-\s]?\d{5}\b")
_AADHAAR_RE = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# Priority order: when two spans overlap, the earlier category in this list
# wins (Aadhaar's 12 digits are checked before phone's 10, etc).
_REGEX_CATEGORIES: list[tuple[str, re.Pattern]] = [
    ("AADHAAR", _AADHAAR_RE),
    ("PHONE", _PHONE_RE),
    ("PAN", _PAN_RE),
    ("EMAIL", _EMAIL_RE),
]

_PRIORITY = {"AADHAAR": 0, "PHONE": 1, "PAN": 2, "EMAIL": 3, "PERSON": 4}


def _name_matches(text: str, names: list[str]) -> list[tuple[int, int, str, str]]:
    matches: list[tuple[int, int, str, str]] = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        for m in re.finditer(r"\b" + re.escape(name) + r"\b", text):
            matches.append((m.start(), m.end(), "PERSON", m.group()))
    return matches


def mask(text: str, names: list[str] | None = None) -> tuple[str, dict[str, str]]:
    """Replace PII in `text` with stable `[TYPE_n]` placeholders.

    `names` are model-detected person-name spans (verbatim substrings of
    `text`) — the one category regex can't find on its own.

    Returns (masked_text, mask_map) where mask_map maps placeholder -> the
    original substring it replaced, so unmask() can reverse it exactly.
    Numbering is stable: the same original value always gets the same
    placeholder, assigned in order of first appearance.
    """
    candidates: list[tuple[int, int, str, str]] = []
    for category, pattern in _REGEX_CATEGORIES:
        for m in pattern.finditer(text):
            candidates.append((m.start(), m.end(), category, m.group()))
    candidates.extend(_name_matches(text, names or []))

    candidates.sort(key=lambda c: (c[0], _PRIORITY[c[2]]))

    kept: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, category, matched in candidates:
        if start < last_end:
            continue  # overlaps a higher-priority span already kept
        kept.append((start, end, category, matched))
        last_end = end

    mask_map: dict[str, str] = {}
    placeholder_for: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    out: list[str] = []
    cursor = 0
    for start, end, category, matched in kept:
        out.append(text[cursor:start])
        key = (category, matched)
        placeholder = placeholder_for.get(key)
        if placeholder is None:
            counters[category] = counters.get(category, 0) + 1
            placeholder = f"[{category}_{counters[category]}]"
            placeholder_for[key] = placeholder
            mask_map[placeholder] = matched
        out.append(placeholder)
        cursor = end
    out.append(text[cursor:])

    return "".join(out), mask_map


def unmask(text: str, mask_map: dict[str, str]) -> str:
    """Reverse substitution: every placeholder in `text` back to its original."""
    for placeholder, original in mask_map.items():
        text = text.replace(placeholder, original)
    return text
