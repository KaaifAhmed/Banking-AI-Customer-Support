"""
Input/output guards for AI-generated content — docs/ai-system.md §5.1.
Imported by ai-worker and background-worker. Anything reaching an
external channel (WhatsApp) or stored as a job result goes through
these first. Pattern-based, not a full injection/DLP scanner — flags
the common cases, doesn't try to catch everything.
"""
import re

MAX_INPUT_LENGTH = 8000

INJECTION_PATTERNS = [
    r"ignore (all|any|previous) instructions",
    r"disregard (the )?system prompt",
    r"reveal (your|the) system prompt",
    r"you are now",
]

SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",      # generic API-key-shaped string
    r"AIza[0-9A-Za-z\-_]{35}",   # Google-style key
]


def input_guard(text: str) -> dict:
    """Flags likely prompt injection. Flags + logs by default rather than
    hard-blocking — tighten to a hard block at kickoff if the theme's
    risk profile warrants it."""
    if not text or len(text) > MAX_INPUT_LENGTH:
        return {"ok": False, "flagged": True, "reason": "empty_or_too_long"}
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return {"ok": True, "flagged": True, "reason": f"matched: {pattern}"}
    return {"ok": True, "flagged": False, "reason": None}


def output_guard(text: str) -> dict:
    """Blocks obvious credential/secret leakage before anything leaves the system."""
    if not text:
        return {"ok": True, "reason": None}
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            return {"ok": False, "reason": "possible_secret_leak"}
    return {"ok": True, "reason": None}
