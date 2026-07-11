#!/usr/bin/env python3
"""Hygiene check: no hardcoded study numbers in site HTML.

Rule: text nodes in site/*.html must not contain digits. Every study number
is injected client-side from site/figures.json into elements carrying a
data-fig attribute. The only exceptions are elements (and their subtrees)
explicitly marked data-static-ok="reason" — reserved for non-study numerals
such as dates inside verbatim citations of IMI documents.

Stdlib-only so CI can run it before the environment is synced.
"""

import sys
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"


class Checker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.static_ok_depth = 0
        self.skip_depth = 0  # script/style contents are not text
        self.violations: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.static_ok_depth or "data-static-ok" in attrs:
            self.static_ok_depth += 1
        if tag in ("script", "style"):
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if self.static_ok_depth:
            self.static_ok_depth -= 1
        if tag in ("script", "style") and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth or self.static_ok_depth:
            return
        if any(ch.isdigit() for ch in data):
            line = self.getpos()[0]
            self.violations.append((line, data.strip()[:80]))


def main() -> int:
    failed = False
    for path in sorted(SITE.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        # Files rendered by the pipeline FROM figures.json are exempt: their
        # numbers cannot drift because CI regenerates and byte-compares them.
        if "GENERATED-FROM-FIGURES" in text[:400]:
            continue
        checker = Checker()
        checker.feed(text)
        for line, text in checker.violations:
            print(f"{path}:{line}: digit in text node: {text!r}")
            failed = True
    if failed:
        print("\nHardcoded numbers found. Inject them from figures.json "
              "(data-fig) or mark the element data-static-ok with a reason.")
        return 1
    print("OK: no hardcoded numbers in site HTML.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
