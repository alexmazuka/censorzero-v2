"""Parser regression on committed real-world HTML fixtures.

If Ukrinform / Pravda / Suspilne change their markup, these fail in CI — the
snapshot parser is pinned to layouts that actually existed.
"""

import json
from pathlib import Path

import pytest

from censorzero.snapshot.parsers import PARSERS

FIX = Path(__file__).parent / "fixtures"
EXPECTED = json.loads((FIX / "expected.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("fname", sorted(EXPECTED))
def test_parser_fields(fname):
    exp = EXPECTED[fname]
    html = (FIX / fname).read_text(encoding="utf-8")
    fields = PARSERS[exp["outlet"]](exp["url"], html)

    assert fields.parse_error is None, fields.parse_error
    assert fields.outlet == exp["outlet"]
    if exp.get("rubric"):
        assert fields.rubric == exp["rubric"]
    assert (fields.date_published or "").startswith(exp["date_published_prefix"]), \
        f"{fname}: date {fields.date_published!r}"
    if exp["title_contains"]:
        assert exp["title_contains"] in (fields.title or ""), fields.title
    assert len(fields.body_text or "") >= exp["body_min_len"], \
        f"{fname}: body len {len(fields.body_text or '')}"


def test_all_fixtures_have_expectations():
    present = {p.name for p in FIX.glob("*.html")}
    assert present == set(EXPECTED), (present ^ set(EXPECTED))
