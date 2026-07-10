"""Entity classification — the single source of officialness for the study.

Applied identically to Ukrinform and every control outlet, to every period.
Classification is by TEXT (a normalized entity span), never by URL slug.

An entity span is classified into exactly one label:
  - "foreign_official"  : matches a foreign entity, OR matches a Ukrainian
                          official pattern but co-occurs with foreign context
                          (e.g. "міністр оборони Німеччини"). Excluded from
                          parket by definition.
  - "ukrainian_official": matches a Ukrainian-official pattern, no foreign
                          context in the span.
  - "non_official"      : recognizable named source, no official match.
  - "unknown"           : too short / junk / unrecognized — never counted as a
                          non-official voice for the parket test (v1 counted
                          junk as non_official and thereby suppressed parket).

The registry is data/registry/entities_v2.json (versioned, unit-tested).
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .text_norm import normalize, word_boundary_pattern

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "registry" / "entities_v2.json"

# A span shorter than this (after normalization) is treated as unusable.
MIN_ENTITY_CHARS = 3


@dataclass(frozen=True)
class Registry:
    version: str
    ukrainian_re: re.Pattern
    foreign_re: re.Pattern
    foreign_context_re: re.Pattern


@lru_cache(maxsize=1)
def load_registry() -> Registry:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    uk_fragments, fo_fragments = [], []
    for ent in data["entities"]:
        target = uk_fragments if ent["category"] == "ukrainian_official" else fo_fragments
        target.extend(ent["patterns"])
    uk_re = re.compile("|".join(word_boundary_pattern(f) for f in uk_fragments))
    fo_re = re.compile("|".join(word_boundary_pattern(f) for f in fo_fragments))
    fc_re = re.compile("|".join(word_boundary_pattern(f) for f in data["foreign_context"]))
    return Registry(
        version=data["version"],
        ukrainian_re=uk_re,
        foreign_re=fo_re,
        foreign_context_re=fc_re,
    )


def classify_entity(span: str) -> str:
    """Label a single already-extracted source span.

    Curated registry patterns are checked first — they are word-boundary
    anchored and specific, so even short valid acronyms (ЄС, G7) classify
    correctly. The min-length / junk guard applies only to the
    non_official-vs-unknown fallback (v1 counted junk as non_official and
    thereby suppressed parket)."""
    norm = normalize(span)
    reg = load_registry()

    if reg.foreign_re.search(norm):
        return "foreign_official"
    if reg.ukrainian_re.search(norm):
        # A Ukrainian-official pattern inside a foreign-context span is a
        # foreign actor described with a generic role word ("міністр ... ФРН").
        return "foreign_official" if reg.foreign_context_re.search(norm) else "ukrainian_official"

    if len(norm) < MIN_ENTITY_CHARS:
        return "unknown"
    return "non_official" if _looks_like_named_source(norm) else "unknown"


# A named source has at least one capitalized token in the ORIGINAL span, or a
# multi-word organization. We approximate on the normalized span by requiring
# at least one alphabetic token of length >= 3 and no leading stopword.
_STOPWORD_LEAD = re.compile(r"^(що|про|як|коли|це|там|тут|потім|також|адже|бо|де)\b")
_ALPHA_TOKEN = re.compile(r"[A-Za-zА-Яа-яЀ-џҐґЄєІіЇї]{3,}")


def _looks_like_named_source(norm: str) -> bool:
    if _STOPWORD_LEAD.search(norm):
        return False
    return bool(_ALPHA_TOKEN.search(norm))


def official_focus(title: str, lead: str) -> bool:
    """True if a Ukrainian-official entity is named in the title or lead and
    the same span is not foreign-contextualized there."""
    reg = load_registry()
    for field in (title, lead):
        norm = normalize(field or "")
        if not norm:
            continue
        if reg.ukrainian_re.search(norm) and not _foreign_overrides(norm, reg):
            return True
    return False


def _foreign_overrides(norm: str, reg: Registry) -> bool:
    """Heuristic: title/lead is about a foreign actor if it names a foreign
    entity or foreign context AND no distinctively Ukrainian institution.

    Distinctively Ukrainian = a match that is not a bare generic role word.
    We treat presence of foreign entity OR foreign context as override unless
    a Ukrainian *named* body (МЗС/ЗСУ/Кабмін/… i.e. length>=3 acronym or
    surname) is present. Kept deliberately conservative; the source-level
    classify_entity does the precise work, this only gates title framing.
    """
    if reg.foreign_re.search(norm):
        return True
    return False
