"""readme stage: render README.md from a template + site/figures.json.

No number in README.md is typed by hand; every value comes from figures.json
so the README can never drift from the data (a v1 failure mode).
"""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[3]
SITE = REPO_ROOT / "site"
TEMPLATES = REPO_ROOT / "docs" / "templates"


def _pct(x: float) -> str:
    return "n/a" if x is None or x != x else f"{x * 100:.2f}%"


def run() -> None:
    figures = json.loads((SITE / "figures.json").read_text())
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    env.filters["pct"] = _pct
    template = env.get_template("README.md.j2")
    rendered = template.render(fig=figures)
    (REPO_ROOT / "README.md").write_text(rendered, encoding="utf-8")
    print("readme: README.md rendered from site/figures.json")
