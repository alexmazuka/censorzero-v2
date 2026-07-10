"""Ukrainian text normalization shared by extraction and classification.

Kept tiny and dependency-free so both the classifier and its tests import the
exact same normalization — a mismatch here was a v1 failure mode.
"""

import re
import unicodedata

# Apostrophe variants Ukrainian text uses interchangeably -> one canonical form.
APOSTROPHES = "'’‘`ʼ"
_APOS_RE = re.compile(f"[{APOSTROPHES}]")

# A "word character" for Ukrainian: Cyrillic + Latin letters and digits.
# Used to build word-boundary lookarounds (substring matching is forbidden).
WORD = r"[0-9A-Za-zА-Яа-яЀ-џҐґЄєІіЇї'’]"
NOT_WORD_BEHIND = rf"(?<!{WORD})"
NOT_WORD_AHEAD = rf"(?!{WORD})"


def normalize(text: str) -> str:
    """NFC, unify apostrophes, lowercase, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = _APOS_RE.sub("'", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def word_boundary_pattern(fragment: str) -> str:
    """Wrap a regex fragment in Ukrainian word boundaries.

    The fragment is used as-is (it may contain its own alternations/anchors);
    we only guarantee it cannot match inside a larger word.
    """
    return f"{NOT_WORD_BEHIND}(?:{fragment}){NOT_WORD_AHEAD}"
