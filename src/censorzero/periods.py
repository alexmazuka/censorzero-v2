"""Study period definitions.

Boundaries are preregistered in PREREGISTRATION.md (see section "Periods and
their justification"). They are defined once here and imported everywhere;
no other module may restate these dates.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Period:
    key: str
    start: date  # inclusive
    end: date  # inclusive
    label_ua: str
    label_en: str


PERIODS: tuple[Period, ...] = (
    Period(
        key="P0",
        start=date(2023, 5, 1),
        end=date(2023, 10, 31),
        label_ua="До призначення Мацуки — Укрінформ у Білому списку",
        label_en="Before Matsuka's appointment — Ukrinform on the White List",
    ),
    Period(
        key="P1",
        start=date(2023, 11, 9),
        end=date(2024, 4, 25),
        label_ua="Період керівництва Мацуки — виключений з Білого списку",
        label_en="Matsuka's tenure — excluded from the White List",
    ),
    Period(
        key="P2",
        start=date(2025, 7, 1),
        end=date(2025, 12, 15),
        label_ua="Після відходу Мацуки — повернутий до Білого списку",
        label_en="After Matsuka's departure — returned to the White List",
    ),
)


def period_of(d: date) -> str | None:
    """Return the period key for a publication date, or None if outside all."""
    for p in PERIODS:
        if p.start <= d <= p.end:
            return p.key
    return None
