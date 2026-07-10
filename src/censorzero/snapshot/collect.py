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
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from ..periods import PERIODS
from .http import fetch, make_client
from .parsers import PARSERS

# Slack around period edges so edit-shifted lastmods are not dropped pre-fetch;
# exact period membership is decided later from JSON-LD datePublished.
_EDGE_SLACK = timedelta(days=4)
_V1_CHANNELS = {"v1_p0", "v1_corpus", "v1_recovered"}  # period-scoped inventories

REPO_ROOT = Path(__file__).resolve().parents[3]
DISCOVERY_DIR = REPO_ROOT / "data" / "raw" / "discovery"
SPOOL_DIR = REPO_ROOT / "cache" / "spool"  # gitignored
HTML_CACHE = REPO_ROOT / "cache" / "html"  # gitignored
RAW_ARTICLES = REPO_ROOT / "data" / "raw" / "articles"

# Gentle by default: news sites IP-throttle bursts. These values keep the
# crawl polite and, with the batch-cooldown logic below, self-healing.
# "wayback" is the Web Archive transport (see fetch_url below): it does not
# IP-ban like the origins and serves stable, timestamped, original-HTML
# snapshots — more reproducible than the live site (whose 2023 sitemaps have
# expired anyway). It is the primary transport; origins are a fallback.
PER_HOST_CONCURRENCY = {"ukrinform": 4, "pravda": 3, "suspilne": 5, "wayback": 5}

# web/<t>id_/URL returns the raw archived HTML (no Wayback chrome) closest to
# timestamp <t>; "2" resolves to the earliest capture — nearest to publication.
WAYBACK_TPL = "http://web.archive.org/web/2id_/{url}"
BATCH_SIZE = 200
INTER_BATCH_SLEEP = 1.5       # politeness pause between batches (seconds)
COOLDOWN_SLEEP = 90           # cooling pause after a mostly-failed batch
COOLDOWN_FAIL_RATE = 0.5      # batch failure rate that triggers a cooldown
MAX_CONSECUTIVE_BAD_BATCHES = 6  # abort if the host stays blocked this long

SNAPSHOT_COLUMNS = [
    "url", "outlet", "date_published", "date_modified", "rubric", "slug",
    "title", "og_description", "body_text", "parse_error", "parser_version",
    "fetch_status", "final_url", "source", "discovery_channels", "sitemap_lastmod",
]


def _lastmod_in_period(lastmod: str) -> bool:
    if not lastmod:
        return False
    try:
        d = datetime.fromisoformat(lastmod.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            d = date.fromisoformat(lastmod[:10])
        except ValueError:
            return False
    return any(p.start - _EDGE_SLACK <= d <= p.end + _EDGE_SLACK for p in PERIODS)


def _in_scope(row: dict) -> bool:
    """Whether to FETCH this discovered URL. Discovery keeps everything; we
    fetch only what can plausibly fall in a period (v1 inventories are already
    period-scoped; sitemap-only URLs are gated by lastmod ± slack)."""
    channels = set(row["channels"].split("|"))
    if channels & _V1_CHANNELS:
        return True
    return _lastmod_in_period(row["sitemap_lastmod"])


# Суспільне is a SECONDARY, descriptive control (PREREGISTRATION §6). Wayback
# CDX discovers ~170k article URLs across the three windows — far more than is
# needed for a descriptive comparison and infeasible to fetch politely. We
# fetch a deterministic even-stride sample of this size (documented as a
# Deviation). УП (primary control) and Ukrinform are fetched in full.
SUSPILNE_SAMPLE_TARGET = 12000


def _suspilne_sample(rows: list[dict]) -> list[dict]:
    rows = sorted(rows, key=lambda r: r["url"])
    if len(rows) <= SUSPILNE_SAMPLE_TARGET:
        return rows
    stride = len(rows) / SUSPILNE_SAMPLE_TARGET  # even, deterministic
    picked = [rows[int(i * stride)] for i in range(SUSPILNE_SAMPLE_TARGET)]
    return picked


def load_universe(outlet: str, scoped: bool = True) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    gz = DISCOVERY_DIR / "url_universe.csv.gz"
    plain = DISCOVERY_DIR / "url_universe.csv"
    opener = (lambda: gzip.open(gz, "rt", newline="", encoding="utf-8")) if gz.exists() \
        else (lambda: open(plain, newline="", encoding="utf-8"))
    with opener() as fh:
        rows = [r for r in csv.DictReader(fh) if r["outlet"] == outlet]
    if scoped and outlet == "ukrinform":
        rows = [r for r in rows if _in_scope(r)]
    if outlet == "suspilne":
        rows = _suspilne_sample(rows)
    return rows


def _spool_path(outlet: str) -> Path:
    SPOOL_DIR.mkdir(parents=True, exist_ok=True)
    # Plain JSONL: robust to append/resume and readable mid-run, unlike a
    # gzip stream (which lacks an EOF marker until closed).
    return SPOOL_DIR / f"{outlet}.jsonl"


def _iter_spool(path: Path):
    if not path.exists():
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # tolerate a trailing partial line


def _done_urls(outlet: str) -> set[str]:
    """URLs that need no refetch: a successful 200, OR a deterministic parse
    failure of a 200 (refetching won't change it). Transport/HTTP failures
    (429/5xx/timeout) are NOT 'done', so a later gentle pass retries them —
    this makes repeated runs converge instead of freezing early losses."""
    done: set[str] = set()
    for rec in _iter_spool(_spool_path(outlet)):
        if "url" in rec and rec.get("fetch_status") == 200:
            # a 200 means we obtained a page (parse failure is treated as a
            # permanent no-capture / layout miss, not retried); only transport
            # failures (429/5xx/timeout, status != 200) are retried.
            done.add(rec["url"])
    return done


def _cache_html(url: str, html: str) -> None:
    h = hashlib.sha256(url.encode()).hexdigest()
    dest = HTML_CACHE / h[:2] / f"{h}.html.gz"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with gzip.open(dest, "wt", encoding="utf-8") as fh:
            fh.write(url + "\n")
            fh.write(html)


async def fetch_outlet(outlet: str, limit: int | None = None,
                       max_passes: int = 6, via: str = "wayback",
                       sample: int | None = None) -> None:
    """Fetch every in-scope URL, retrying transient failures across passes.

    via: "wayback" (default, archival snapshots) or "origin" (live site).
    sample: if set, restrict to a seeded-shuffle prefix of the universe so a
    run yields a defined stratified-ish subset; continuing (larger sample or
    none) extends the same ordering toward a census.

    A pass fetches all not-yet-successful URLs. Because _done_urls counts only
    200s, each pass retries the 429/5xx/timeout losses of the previous one.
    Passes stop when a pass adds no new successes or max_passes is reached."""
    universe = load_universe(outlet)
    # Always fetch in a deterministic shuffled order. URL order groups articles
    # by rubric and by date, so a partial (still-running) collection would
    # otherwise cover only one rubric/period; a seeded shuffle makes any prefix
    # representative across period x rubric. --sample takes a prefix of it.
    from ..canonical import rng
    g = rng(4242)
    order = g.permutation(len(universe)).tolist()
    universe = [universe[i] for i in order]
    if sample:
        universe = universe[:sample]
    for pass_i in range(1, max_passes + 1):
        done_before = len(_done_urls(outlet))
        todo = [r for r in universe if r["url"] not in _done_urls(outlet)]
        if limit:
            todo = todo[:limit]
        print(f"{outlet}[{via}]: pass {pass_i} universe={len(universe)} "
              f"done={done_before} todo={len(todo)}", flush=True)
        if not todo:
            print(f"{outlet}: complete ({done_before} fetched)", flush=True)
            return
        await _fetch_pass(outlet, todo, via)
        done_after = len(_done_urls(outlet))
        gained = done_after - done_before
        print(f"{outlet}: pass {pass_i} gained {gained} successes "
              f"({done_after}/{len(universe)})", flush=True)
        if gained == 0:
            print(f"{outlet}: no progress this pass — stopping "
                  f"({done_after}/{len(universe)} fetched)", flush=True)
            return
        if limit:  # a limited (pilot) run does a single pass
            return
        await asyncio.sleep(INTER_BATCH_SLEEP * 4)


async def _fetch_pass(outlet: str, todo: list[dict], via: str) -> None:
    parser = PARSERS[outlet]
    conc = PER_HOST_CONCURRENCY["wayback" if via == "wayback" else outlet]
    sem = asyncio.Semaphore(conc)
    spool = open(_spool_path(outlet), "a", encoding="utf-8")
    lock = asyncio.Lock()
    counters = {"ok": 0, "http_fail": 0, "parse_fail": 0}

    async def one(row: dict) -> None:
        fetch_url = WAYBACK_TPL.format(url=row["url"]) if via == "wayback" else row["url"]
        res = await fetch(client, sem, fetch_url)
        # A Wayback "no capture" page can return 200 with an error body; the
        # parser then reports a parse_error and the URL is retried/left unfetched.
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
            fetch_status=res.status, final_url=res.final_url, source=via,
            discovery_channels=row["channels"], sitemap_lastmod=row["sitemap_lastmod"],
        )
        async with lock:
            spool.write(json.dumps(fields, ensure_ascii=False) + "\n")

    client = make_client()
    consecutive_bad = 0
    async with client:
        for i in range(0, len(todo), BATCH_SIZE):
            before = dict(counters)
            batch = todo[i:i + BATCH_SIZE]
            await asyncio.gather(*(one(r) for r in batch))
            spool.flush()  # crash-safe + observable checkpoint every batch
            n = sum(counters.values())
            batch_fail = counters["http_fail"] - before["http_fail"]
            fail_rate = batch_fail / max(1, len(batch))
            print(f"{outlet}: {n}/{len(todo)} {counters} (batch fail {fail_rate:.0%})",
                  flush=True)
            if fail_rate >= COOLDOWN_FAIL_RATE:
                consecutive_bad += 1
                if consecutive_bad >= MAX_CONSECUTIVE_BAD_BATCHES:
                    spool.close()
                    raise SystemExit(
                        f"{outlet}: {consecutive_bad} consecutive mostly-failed "
                        f"batches — host appears to be blocking. Stopping so the "
                        f"spool is preserved; rerun later to resume."
                    )
                print(f"{outlet}: cooling down {COOLDOWN_SLEEP}s (likely throttled)",
                      flush=True)
                await asyncio.sleep(COOLDOWN_SLEEP)
            else:
                consecutive_bad = 0
                await asyncio.sleep(INTER_BATCH_SLEEP)
    spool.close()
    print(f"{outlet} DONE: {counters}", flush=True)


def shard() -> None:
    """Spool -> deterministic parquet shards + hashes + failure report."""
    RAW_ARTICLES.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    hashes: dict[str, str] = {}

    for spool_path in sorted(SPOOL_DIR.glob("*.jsonl")):
        outlet = spool_path.name.split(".")[0]
        records: dict[str, dict] = {}
        for rec in _iter_spool(spool_path):
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
