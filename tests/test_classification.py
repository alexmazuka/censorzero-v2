"""Classifier unit tests.

Includes the exact v1 substring false positives (§3 of the autopsy) as
regression guards, first-person surnames (absent in v1), and foreign-official
exclusion.
"""

import re

import pytest

from censorzero import classification as clf
from censorzero.text_norm import word_boundary_pattern

# --- Ukrainian-official positives ------------------------------------------
UKRAINIAN_OFFICIAL = [
    "Зеленський", "Володимир Зеленський", "Президент України", "Офіс Президента",
    "Єрмак", "Андрій Єрмак", "Кабмін", "Кабінет міністрів", "Прем'єр-міністр Шмигаль",
    "Денис Шмигаль", "Юлія Свириденко", "Верховна Рада", "нардеп", "Стефанчук",
    "міністр закордонних справ", "МЗС", "Кулеба", "Сибіга", "Міноборони", "Умєров",
    "МВС", "Клименко", "Генштаб", "ЗСУ", "Сили оборони", "Сирський", "Залужний",
    "СБУ", "Малюк", "ГУР", "Буданов", "ДПСУ", "ДСНС", "Нацгвардія", "НБУ",
    "Укренерго", "Укрзалізниця", "Нафтогаз", "мер Кличко", "Кличко",
    "облрада", "ОВА", "голова ОВА", "НАБУ", "САП", "генпрокурор", "омбудсман Лубінець",
]

# --- Foreign-official (must be excluded from parket) ------------------------
FOREIGN_OFFICIAL = [
    "НАТО", "ЄС", "Євросоюз", "Єврокомісія", "ООН", "ОБСЄ", "G7", "МВФ",
    "Держдепартамент США", "Пентагон", "Білий дім", "Бундестаг",
    "МЗС РФ", "Кремль", "Лавров", "Путін", "Байден", "Трамп", "Макрон",
    "Шольц", "міністр оборони Німеччини", "президент Польщі", "Дуда",
    "прем'єр Британії", "Столтенберг", "фон дер Ляєн",
]

# --- Must NOT be Ukrainian/foreign official (v1 substring bugs) -------------
NOT_OFFICIAL = [
    "Калашнікова",       # 'ова' must not fire (regional 'ова')
    "набуде чинності",   # 'набу' must not fire (НАБУ)
    "Америки",           # 'мер' must not fire (мер)
    "американська компанія",
    "у Фейсбуці",        # 'сбу' must not fire
    "зросла",            # 'рос'/foreign-context must not fire
    "просто",            # 'рос'
    "гуртожиток",        # 'гур'
    "сапер",             # 'сап'
    "основа",            # 'ова'
    "мова",
    "Іван Петренко",     # ordinary person
    "місцевий житель",
    "експерт Марія",
]


@pytest.mark.parametrize("span", UKRAINIAN_OFFICIAL)
def test_ukrainian_official(span):
    assert clf.classify_entity(span) == "ukrainian_official", span


@pytest.mark.parametrize("span", FOREIGN_OFFICIAL)
def test_foreign_official(span):
    assert clf.classify_entity(span) == "foreign_official", span


@pytest.mark.parametrize("span", NOT_OFFICIAL)
def test_not_official(span):
    label = clf.classify_entity(span)
    assert label in ("non_official", "unknown"), f"{span} -> {label}"


def test_zelensky_present_in_registry():
    # v1 omitted first-person surnames from source markers; guard against
    # regressing to that.
    assert clf.classify_entity("Зеленський") == "ukrainian_official"


def _generate_match(fragment: str) -> str:
    """Deterministically build one string the fragment matches.

    Handles the registry's regex dialect: lookarounds, (?:...) and (...)
    groups with | alternatives, [...]? optional classes, X? optional chars,
    \\w+ / \\s / \\d. Picks the first alternative and drops all optionals, so
    a match is guaranteed to exist iff the fragment is satisfiable.
    """
    s = fragment
    s = re.sub(r"\(\?[=!][^)]*\)", "", s)      # lookaheads
    s = re.sub(r"\(\?<[=!][^)]*\)", "", s)     # lookbehinds
    s = s.replace("(?:", "(")
    # Collapse innermost groups repeatedly, honoring a trailing '?'.
    group = re.compile(r"\(([^()]*)\)(\?)?")
    while True:
        m = group.search(s)
        if not m:
            break
        body, optional = m.group(1), m.group(2)
        repl = "" if optional else body.split("|")[0]
        s = s[:m.start()] + repl + s[m.end():]
    s = re.sub(r"\[[^\]]*\]\?", "", s)          # optional char classes
    s = re.sub(r"\[([^\]]*)\]", lambda m: m.group(1)[0], s)  # required class -> first char
    s = re.sub(r"\\w\+|\\w", "х", s)
    s = re.sub(r"\\d\+|\\d", "1", s)
    s = s.replace("\\s", " ")
    s = re.sub(r"(.)\?", "", s)                  # optional single char/escape
    s = s.replace("\\", "")
    return s.strip()


def test_every_registry_pattern_is_reachable():
    """Each pattern fragment must match its generated exemplar (kills dead
    entries like v1's never-firing 'urad' and 'ofis-prezidenta')."""
    import json

    data = json.loads(clf.REGISTRY_PATH.read_text(encoding="utf-8"))
    groups = [("entity", e["patterns"]) for e in data["entities"]]
    groups.append(("foreign_context", data["foreign_context"]))
    for _kind, frags in groups:
        for frag in frags:
            pat = re.compile(word_boundary_pattern(frag))
            probe = _generate_match(frag)
            assert probe, f"empty probe for {frag!r}"
            assert pat.search(f" {probe} "), f"unreachable pattern {frag!r} (probe {probe!r})"


def test_foreign_context_overrides_generic_role():
    # generic Ukrainian role word + foreign country -> foreign
    assert clf.classify_entity("міністр закордонних справ Польщі") == "foreign_official"
    # but a distinctly Ukrainian body stays Ukrainian
    assert clf.classify_entity("МЗС України") == "ukrainian_official"
