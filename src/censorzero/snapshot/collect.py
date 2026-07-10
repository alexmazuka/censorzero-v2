"""Article fetching and raw-snapshot sharding.

Flow:
  url_universe.csv -> fetch (resumable JSONL spool, gitignored, plus a local
  HTML cache for parser re-runs) -> shard (deterministic zstd parquet under
  data/raw/articles/ + SHA-256 manifest).

Every URL ends up in exactly one of: a parquet row (fetched+parsed), or the
fetch-failure report (data/raw/fetch_failures.csv). Nothing is silently
dropped.
"""

import asyncio
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from .http import fetch, make_client
from .parsers import PARSERS

REPO_ROOT = Path(__file__).resolve().parents[3]
DISCOVERY_DIR = REPO_ROOT / "data" / "raw" / "discovery"
SPOOL_DIR = REPO_ROOT / "cache" / "spool"  # gitignored
HTML_CACHE = REPO_ROOT / "cache" / "html"  # gitignored
RAW_ARTICLES = REPO_ROOT / "data" / "raw" / "articles"

PER_HOST_CONCURRENCY = {"ukrinform": 8, "pravda": 6, "suspilne": 6}

SNAPSHOT_COLUMNS = [
    "url", "outlet", "date_published", "date_modified", "rubric", "slug",
    "title", "og_description", "body_text", "parse_error", "parser_version",
    "fetch_status", "final_url", "discovery_channels", "sitemap_lastmod",
]


def load_universe(outlet: str) -> list[dict]:
    path = DISCOVERY_DIR / "url_universe.csv"
    csv.field_size_limit(sys.maxsize)
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["outlet"] == outlet]


def _spool_path(outlet: str) -> Path:
    SPOOL_DIR.mkdir(parents=True, exist_ok=True)
    return SPOOL_DIR / f"{outlet}.jsonl.gz"


def _done_urls(outlet: str) -> set[str]:
    path = _spool_path(outlet)
    done: set[str] = set()
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["url"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return done


def _cache_html(url: str, html: str) -> None:
    h = hashlib.sha256(url.encode()).hexdigest()
    dest = HTML_CACHE / h[:2] / f"{h}.html.gz"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with gzip.open(dest, "wt", encoding="utf-8") as fh:
            fh.write(url + "\n")
            fh.write(html)


async def fetch_outlet(outlet: str, limit: int | None = None) -> None:
    universe = load_universe(outlet)
    done = _done_urls(outlet)
    todo = [r for r in universe if r["url"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"{outlet}: universe={len(universe)} done={len(done)} todo={len(todo)}",
          flush=True)
    if not todo:
        return

    parser = PARSERS[outlet]
    sem = asyncio.Semaphore(PER_HOST_CONCURRENCY[outlet])
    spool = gzip.open(_spool_path(outlet), "at", encoding="utf-8")
    lock = asyncio.Lock()
    counters = {"ok": 0, "http_fail": 0, "parse_fail": 0}

    async def one(row: dict) -> None:
        res = await fetch(client, sem, row["url"])
        if res.status == 200 and res.text:
            _cache_html(row["url"], res.text)
            try:
                fields = parser(row["url"], res.text).to_dict()
            except Exception as exc:  # parser bug: record, never crash the run
                fields = {"url": row["url"], "outlet": outlet,
                          "parse_error": f"exception: {exc}"}
            counters["parse_fail" if fields.get("parse_error") else "ok"] += 1
        else:
            fields = {"url": row["url"], "outlet": outlet}
            counters["http_fail"] += 1
        fields.update(
            fetch_status=res.status, final_url=res.final_url,
            discovery_channels=row["channels"], sitemap_lastmod=row["sitemap_lastmod"],
        )
        async with lock:
            spool.write(json.dumps(fields, ensure_ascii=False) + "\n")
            n = sum(counters.values())
            if n % 500 == 0:
                spool.flush()
                print(f"{outlet}: {n}/{len(todo)} {counters}", flush=True)

    client = make_client()
    async with client:
        BATCH = 200
        for i in range(0, len(todo), BATCH):
            await asyncio.gather(*(one(r) for r in todo[i:i + BATCH]))
    spool.close()
    print(f"{outlet} DONE: {counters}", flush=True)


def shard() -> None:
    """Spool -> deterministic parquet shards + hashes + failure report."""
    RAW_ARTICLES.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    hashes: dict[str, str] = {}

    for spool_path in sorted(SPOOL_DIR.glob("*.jsonl.gz")):
        outlet = spool_path.name.split(".")[0]
        records: dict[str, dict] = {}
        with gzip.open(spool_path, "rt", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                records[rec["url"]] = rec  # last write wins (retried URLs)
        rows = []
        for rec in records.values():
            if rec.get("fetch_status") == 200 and not rec.get("parse_error"):
                rows.append({c: rec.get(c) for c in SNAPSHOT_COLUMNS})
            else:
                failures.append({
                    "outlet": outlet, "url": rec["url"],
                    "fetch_status": rec.get("fetch_status"),
                    "parse_error": rec.get("parse_error"),
                    "discovery_channels": rec.get("discovery_channels"),
                })
        df = pd.DataFrame(rows, columns=SNAPSHOT_COLUMNS).sort_values("url")
        df["month"] = df["date_published"].str.slice(0, 7)
        for month, part in df.groupby("month", sort=True):
            dest = RAW_ARTICLES / f"{outlet}_{month}.parquet"
            part.drop(columns=["month"]).reset_index(drop=True).to_parquet(
                dest, engine="pyarrow", compression="zstd", index=False,
            )
        undated = df[df["month"].isna()]
        if len(undated):
            dest = RAW_ARTICLES / f"{outlet}_undated.parquet"
            undated.drop(columns=["month"]).reset_index(drop=True).to_parquet(
                dest, engine="pyarrow", compression="zstd", index=False,
            )
        print(f"{outlet}: {len(df)} rows sharded, {len(undated)} undated")

    fail_path = REPO_ROOT / "data" / "raw" / "fetch_failures.csv"
    failures.sort(key=lambda r: (r["outlet"], r["url"]))
    with open(fail_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["outlet", "url", "fetch_status",
                                           "parse_error", "discovery_channels"])
        w.writeheader()
        w.writerows(failures)

    for pq in sorted(RAW_ARTICLES.glob("*.parquet")):
        h = hashlib.sha256()
        h.update(pq.read_bytes())
        hashes[pq.name] = h.hexdigest()
    (RAW_ARTICLES / "SHA256SUMS.json").write_text(
        json.dumps(hashes, indent=1, sort_keys=True) + "\n")
    print(f"failures: {len(failures)} -> {fail_path}")
