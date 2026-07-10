"""Per-article feature computation — the locked metric definitions.

Implements PREREGISTRATION.md section 7 exactly, in one place, imported by
every stage and every outlet. No hand-rolled copy of these formulas may exist
elsewhere (v1 had >= 6).
"""

from dataclasses import asdict, dataclass

from . import classification as clf
from .source_extraction import EXTRACTION_VERSION, extract_sources

CLASSIFIER_VERSION = "2.0.0"


@dataclass
class ArticleFeatures:
    sc: int  # distinct extracted sources
    oc: int  # classified ukrainian_official
    fc: int  # classified foreign_official
    nc: int  # classified non_official
    uc: int  # classified unknown
    official_focus: bool
    parket: bool  # primary outcome (see PREREGISTRATION §7)
    balance_risk: bool  # secondary outcome
    sources_json: str  # full "span::label" list, no truncation
    classifier_version: str = CLASSIFIER_VERSION
    extraction_version: str = EXTRACTION_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _lead(body_text: str) -> str:
    """First body paragraph (for official-focus framing)."""
    if not body_text:
        return ""
    return body_text.split("\n", 1)[0]


def compute_features(title: str, body_text: str, og_description: str = "") -> ArticleFeatures:
    spans = extract_sources(title, body_text, og_description)
    labels = [clf.classify_entity(s) for s in spans]

    oc = sum(1 for x in labels if x == "ukrainian_official")
    fc = sum(1 for x in labels if x == "foreign_official")
    nc = sum(1 for x in labels if x == "non_official")
    uc = sum(1 for x in labels if x == "unknown")
    sc = len(spans)

    focus = clf.official_focus(title, _lead(body_text))

    # PREREGISTRATION §7 — primary and secondary outcomes.
    # sc == 0 is NEVER parket (v1's fatal flaw); parket requires exactly one
    # source and that it be a Ukrainian official, with no non-official voice.
    parket = bool(focus and sc == 1 and oc == 1 and nc == 0)
    balance_risk = bool(focus and oc >= 1 and nc == 0)

    sources_json = " | ".join(f"{s}::{lab}" for s, lab in zip(spans, labels))

    return ArticleFeatures(
        sc=sc, oc=oc, fc=fc, nc=nc, uc=uc,
        official_focus=focus, parket=parket, balance_risk=balance_risk,
        sources_json=sources_json,
    )
