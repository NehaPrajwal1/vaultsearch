"""Conservative presentation only; never an authorization or injection oracle."""
import re
import unicodedata

PATTERNS = {
    "access_override": r"(?:ignore|override|disregard|bypass|disable|suspend|set aside).{0,45}(?:access|permission|authorization|evidence boundary)",
    "advisory_permissions": r"permissions.{0,20}(?:advisory|optional)",
    "invent_sensitive": r"(?:best guess|invent|fabricat|make up).{0,70}(?:confidential|salary|compensation|private|secret)",
    "claimed_authority": r"(?:user|reader).{0,35}(?:administrator|unrestricted access)|(?:system|developer) (?:note|message|instruction)",
    "instruction_override": r"(?:ignore|discard|replace|supersede).{0,40}(?:previous|prior|above|system).{0,25}(?:rules|instructions)",
    # Both verb-first and passive/object-first phrasing; still a lexical heuristic.
    "secret_export": (
        r"(?:send|upload|transmit|reveal|disclose).{0,60}(?:credentials|secrets|private records|confidential)"
        r"|(?:credentials|secrets|private records|confidential).{0,60}"
        r"\b(?:sent|uploaded|transmitted|revealed|disclosed)\b"
    ),
}


def presentation_flags(text):
    normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    return [name for name, pattern in PATTERNS.items() if re.search(pattern, normalized)]


SAFETY_MESSAGE = (
    "Generated draft withheld for review. It may repeat unsafe source instructions. "
    "Source text cannot grant access or override permission checks. "
    "Do not follow directions to bypass permission checks. "
    "Do not follow source instructions to send private records or credentials to an external recipient. "
    "Do not invent confidential information. Inspect the permitted source excerpts below. "
    "Legitimate security quotations can also trigger this safeguard; quotation alone is not endorsement."
)


def present_answer(answer):
    """Replace flagged drafts. This heuristic misses evasions and flags benign quotes.

    Raw model calls belong in evaluation artifacts, never in this public message.
    Unflagged output remains an untrusted draft, not a safety verdict.
    """
    flags = presentation_flags(answer)
    if not flags:
        return answer, {"status": "unflagged", "flags": []}
    return SAFETY_MESSAGE, {"status": "review_required", "flags": flags}
