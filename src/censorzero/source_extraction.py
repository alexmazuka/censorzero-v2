"""Attribution / source extraction from article body text.

Deterministic, sentence-segmented, no truncation. Returns the full list of
distinct canonical source spans (v1 truncated to 5 and used exact-string dedup;
both are fixed here). The classifier (classification.py) labels each span.

Pattern families mirror the v1 "v2 extractor" set, re-expressed with explicit
boundaries and documented individually. Extraction accuracy is measured against
the gold standard (PREREGISTRATION.md section 9) — these patterns are a
declared proxy, not ground truth.

EXTRACTION_VERSION is recorded with the processed data.
"""

import re

EXTRACTION_VERSION = "1"

# 22 reporting-verb forms (v1 canonical set + the five v1 silently dropped:
# закликав/ла, вважає/ють, прокоментував/ла, інформує, поінформував/ла).
REPORTING_VERBS = (
    "заявив|заявила|заявили|повідомив|повідомила|повідомили|сказав|сказала|сказали|"
    "наголосив|наголосила|наголосили|зауважив|зауважила|додав|додала|додали|"
    "підкреслив|підкреслила|відзначив|відзначила|розповів|розповіла|розповіли|"
    "написав|написала|зазначив|зазначила|зазначили|закликав|закликала|"
    "вважає|вважають|прокоментував|прокоментувала|інформує|поінформував|поінформувала|"
    "повідомляє|повідомляють|уточнив|уточнила|запевнив|запевнила"
)

CAP = r"[А-ЯІЇЄҐA-Z]"

# 1) "<Хтось> заявив/повідомив ..." — actor precedes a reporting verb.
PERSON_RE = re.compile(rf"({CAP}[^.!?\n]{{1,90}}?)\s+(?:{REPORTING_VERBS})\b")

# 2) Lead attributions: "За словами X", "Як повідомив X", "Повідомляє X".
LEADING_RE = re.compile(
    rf"(?:За словами|За даними|За інформацією|Як повідомив|Як повідомила|Як повідомили|"
    rf"Як зазначив|Як зазначила|Як заявив|Як заявила|Повідомляє|Повідомив|Повідомила)\s+"
    rf"({CAP}[^,.;:\n]{{1,90}})"
)

# 3) "Про це повідомляє/йдеться в/сказано в X".
PRO_CE_RE = re.compile(
    rf"[Пп]ро це (?:повідомляє|повідомили|повідомив|повідомила|йдеться\s+(?:в|у)|"
    rf"зазначається\s+(?:в|у)|сказано\s+(?:в|у)|розповів|розповіла|заявив|заявила)\s+"
    rf"({CAP}[^.!?\n]{{2,80}})"
)

# 4) "Як передає Укрінформ, про це <джерело>".
AS_TRANSMITS_RE = re.compile(
    rf"[Яя]к (?:передає|передають|пише|пишуть|повідомляє|повідомляють)\s+"
    rf"[А-ЯІЇЄҐA-Z][^,.\n]{{2,40}},?\s*про це\s+({CAP}[^.!?\n]{{2,70}})"
)

# 5) "повідомили/зазначили в/у/на <орган>".
IN_ORG_RE = re.compile(
    rf"(?:повідомили|зазначили|уточнили|наголосили|підкреслили|сказали|вважають|"
    rf"додали|розповіли|поінформували)\s+(?:в|у|на)\s+({CAP}[^.!?\n]{{2,50}})"
)

# 6) Headline / caption dash attribution: "... — <Джерело>" at end of line.
HEADLINE_SRC_RE = re.compile(
    rf"\s[—–-]\s*({CAP}[А-ЯІЇЄҐа-яіїєґA-Za-z'’\s]{{2,60}}?)\s*$", re.MULTILINE
)

PATTERNS = [PERSON_RE, LEADING_RE, PRO_CE_RE, AS_TRANSMITS_RE, IN_ORG_RE, HEADLINE_SRC_RE]

_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_LEADING_STOP = re.compile(r"^(?:що|про|як|коли|адже|бо|тому що|оскільки)\s+", re.IGNORECASE)
_TRAILING_JUNK = re.compile(r"[\s,.;:—–-]+$")


def _clean_span(span: str) -> str:
    span = span.strip()
    span = _LEADING_STOP.sub("", span)  # v1 regression: restored stripping
    span = _TRAILING_JUNK.sub("", span)
    span = re.sub(r"\s+", " ", span)
    return span.strip()


def _canonical_key(span: str) -> str:
    """Dedup key: lowercased, apostrophes unified, first 6 word-tokens.

    Prevents the same actor captured by two spans of different length from
    counting as two sources (v1 exact-string dedup did not)."""
    from .text_norm import normalize

    toks = re.findall(r"[0-9a-zа-я'ґєії]+", normalize(span))
    return " ".join(toks[:6])


def extract_sources(title: str, body_text: str, og_description: str = "") -> list[str]:
    """Return the full ordered list of distinct source spans.

    Order is first-appearance order (deterministic). No truncation.
    The title and og_description contribute only via the headline-dash and
    lead patterns applied to them (matching v1 behavior for those channels).
    """
    found: list[str] = []
    seen: set[str] = set()

    def consider(raw: str) -> None:
        span = _clean_span(raw)
        if len(span) < 3 or len(span.split()) > 12:
            return
        key = _canonical_key(span)
        if len(key) < 3 or key in seen:
            return
        seen.add(key)
        found.append(span)

    # Body: sentence by sentence so a pattern cannot span across sentences.
    for sentence in _SENT_SPLIT.split(body_text or ""):
        for pat in PATTERNS:
            for m in pat.finditer(sentence):
                consider(m.group(1))

    # Headline-dash attribution on title and og_description.
    for extra in (title or "", og_description or ""):
        for m in HEADLINE_SRC_RE.finditer(extra + "\n"):
            consider(m.group(1))
        for m in LEADING_RE.finditer(extra):
            consider(m.group(1))

    return found
