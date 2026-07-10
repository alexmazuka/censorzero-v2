#!/usr/bin/env python3
"""One-time snapshot collector (the only network-touching entrypoint).

Usage:
  uv run python scripts/01_snapshot.py discover-ukrinform
  uv run python scripts/01_snapshot.py discover-suspilne
  uv run python scripts/01_snapshot.py universe
  uv run python scripts/01_snapshot.py fetch <ukrinform|pravda|suspilne> [--limit N]
  uv run python scripts/01_snapshot.py shard

Note on pravda.com.ua discovery: its day-archive index pages are bot-gated
(Cloudflare challenge), so they are collected once through a real browser
session into data/raw/discovery/pravda_day_archives/ (one file per day,
YYYY-MM-DD.html[.gz]); `universe` then parses those committed files offline.
This is declared in PREREGISTRATION.md section 5/6.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from censorzero.snapshot import collect, discovery  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("discover-ukrinform")
    sub.add_parser("discover-suspilne")
    sub.add_parser("universe")
    f = sub.add_parser("fetch")
    f.add_argument("outlet", choices=["ukrinform", "pravda", "suspilne"])
    f.add_argument("--limit", type=int, default=None)
    sub.add_parser("shard")
    args = ap.parse_args()

    if args.cmd == "discover-ukrinform":
        asyncio.run(discovery.discover_ukrinform())
    elif args.cmd == "discover-suspilne":
        asyncio.run(discovery.discover_suspilne_cdx())
    elif args.cmd == "universe":
        discovery.build_url_universe()
    elif args.cmd == "fetch":
        asyncio.run(collect.fetch_outlet(args.outlet, args.limit))
    elif args.cmd == "shard":
        collect.shard()
    return 0


if __name__ == "__main__":
    sys.exit(main())
