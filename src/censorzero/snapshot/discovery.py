"""URL discovery — the three preregistered channels (PREREGISTRATION.md §5).

Everything discovered is written to data/raw/discovery/ as raw bytes
(sitemap XML, CDX responses, day-archive HTML) so that discovery itself is
auditable and re-parsable offline.
"""

import asyncio
import csv
import gzip
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree

from ..periods import PERIODS
from .http import fetch, make_client

REPO_ROOT = Path(__file__).resolve().parents[3]
DISCOVERY_DIR = REPO_ROOT / "data" / "raw" / "discovery"
BOOTSTRAP_DIR = REPO_ROOT / "data" / "bootstrap" / "v1_inventories"

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
UKRINFORM_WEEK_TPL = "https://www.ukrinform.ua/sitemap/{year}/{week:02d}.xml"
CDX_API = "http://web.archive.org/cdx/search/cdx"

SUSPILNE_ARTICLE_RE = re.compile(r"^https?://suspilne\.media/(\d+)-[a-z0-9-]+/?$")
PRAVDA_NEWS_RE = re.compile(r"^/news/\d{4}/\d{2}/\d{1,2}/\d+/?$")

# Ukrinform rubrics in scope for fetching (primary 7 + world for the S-world
# sensitivity scenario). Filtering here avoids fetching ~40% off-topic URLs.
UKRINFORM_RUBRIC_RE = re.compile(
    r"ukrinform\.ua/(rubric-(?:polytics|economy|society|regions|ato|"
    r"tymchasovo-okupovani|vidbudova|world))/\d"
)


def iso_weeks_for_periods() -> list[tuple[int, int]]:
    """Every ISO (year, week) intersecting any study period, sorted."""
    weeks: set[tuple[int, int]] = set()
    for p in PERIODS:
        d = p.start
        while d <= p.end:
            weeks.add(d.isocalendar()[:2])
            d += timedelta(days=1)
    return sorted(weeks)


def parse_sitemap_xml(xml_text: str) -> list[tuple[str, str]]:
    root = ElementTree.fromstring(xml_text)
    out = []
    for el in root.findall("sm:url", SITEMAP_NS):
        loc = (el.findtext("sm:loc", default="", namespaces=SITEMAP_NS) or "").strip()
        lastmod = (el.findtext("sm:lastmod", default="", namespaces=SITEMAP_NS) or "").strip()
        if loc:
            out.append((loc, lastmod))
    return out


async def _wayback_latest_200(client, sem, url: str) -> str | None:
    """Timestamp of the most recent status-200 Wayback capture of `url`."""
    q = f"{CDX_API}?url={url}&output=json&filter=statuscode:200&fl=timestamp&limit=-5"
    res = await fetch(client, sem, q)
    if not res.text or res.status != 200:
        return None
    try:
        rows = json.loads(res.text)
    except json.JSONDecodeError:
        return None
    return rows[-1][0] if len(rows) > 1 else None


async def discover_ukrinform() -> None:
    """Recover every weekly sitemap: live first, else newest Wayback capture.

    Writes raw XML to data/raw/discovery/ukrinform_sitemaps/{year}-W{week}.xml
    and a per-week status log. Fails loudly if a week yields nothing from
    either channel (bootstrap inventories still cover it downstream, but the
    gap must be visible).
    """
    outdir = DISCOVERY_DIR / "ukrinform_sitemaps"
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = outdir / "_status.json"
    log: dict[str, dict] = json.loads(log_path.read_text()) if log_path.exists() else {}

    client = make_client()
    live_sem = asyncio.Semaphore(4)
    wb_sem = asyncio.Semaphore(3)

    async with client:
        for year, week in iso_weeks_for_periods():
            key = f"{year}-W{week:02d}"
            dest = outdir / f"{key}.xml"
            if dest.exists() and log.get(key, {}).get("ok"):
                continue
            url = UKRINFORM_WEEK_TPL.format(year=year, week=week)
            entry: dict = {"url": url, "ok": False}

            res = await fetch(client, live_sem, url)
            is_sitemap = res.text and "<urlset" in res.text and "404" not in (res.final_url or "")
            if res.status == 200 and is_sitemap:
                dest.write_text(res.text, encoding="utf-8")
                entry.update(ok=True, channel="live", n_urls=len(parse_sitemap_xml(res.text)))
            else:
                entry["live_status"] = res.status
                ts = await _wayback_latest_200(client, wb_sem, url)
                if ts:
                    wb_url = f"http://web.archive.org/web/{ts}id_/{url}"
                    wres = await fetch(client, wb_sem, wb_url)
                    if wres.status == 200 and wres.text and "<urlset" in wres.text:
                        dest.write_text(wres.text, encoding="utf-8")
                        entry.update(
                            ok=True, channel="wayback", wayback_timestamp=ts,
                            n_urls=len(parse_sitemap_xml(wres.text)),
                        )
                    else:
                        entry["wayback_error"] = wres.error or f"http {wres.status}"
                else:
                    entry["wayback_error"] = "no status-200 capture"
            log[key] = entry
            log_path.write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
            print(f"{key}: {'OK ' + entry.get('channel', '') if entry['ok'] else 'MISSING'}",
                  flush=True)

    missing = [k for k, v in log.items() if not v.get("ok")]
    print(f"\nweeks total={len(log)} missing={len(missing)}: {missing}")


async def discover_suspilne_cdx() -> None:
    """Wayback CDX enumeration of suspilne.media national-news URLs.

    Uses resumeKey pagination (the page= API conflicts with a from/to+limit
    query and returns empty). Raw CDX pages written to
    data/raw/discovery/suspilne_cdx/{period}_partNNN.json.
    """
    outdir = DISCOVERY_DIR / "suspilne_cdx"
    outdir.mkdir(parents=True, exist_ok=True)
    client = make_client()
    sem = asyncio.Semaphore(2)
    async with client:
        for p in PERIODS:
            frm, to = p.start.strftime("%Y%m%d"), p.end.strftime("%Y%m%d")
            resume_key = None
            part = 0
            total = 0
            while True:
                dest = outdir / f"{p.key}_part{part:03d}.json"
                base = (
                    f"{CDX_API}?url=suspilne.media&matchType=prefix&from={frm}&to={to}"
                    f"&filter=statuscode:200&filter=mimetype:text/html"
                    f"&collapse=urlkey&fl=original,timestamp&output=json"
                    f"&limit=20000&showResumeKey=true"
                )
                q = base + (f"&resumeKey={resume_key}" if resume_key else "")
                res = await fetch(client, sem, q)
                if res.status != 200 or res.text is None:
                    raise SystemExit(f"CDX failed for {p.key} part {part}: "
                                     f"{res.status} {res.error}")
                rows = json.loads(res.text) if res.text.strip() else []
                data = [r for r in rows[1:] if len(r) == 2]
                keys = [r[0] for r in rows[1:] if len(r) == 1]
                dest.write_text(json.dumps([rows[0]] + data) + "\n" if data else "[]\n")
                total += len(data)
                print(f"suspilne CDX {p.key} part {part}: {len(data)} rows "
                      f"(total {total})", flush=True)
                if keys:
                    resume_key = keys[-1]
                    part += 1
                else:
                    break
            print(f"suspilne CDX {p.key} DONE: {total} urls", flush=True)


def pravda_urls_from_day_archives() -> dict[str, str]:
    """Parse committed UP day-archive HTML into a url -> day mapping."""
    from bs4 import BeautifulSoup

    archive_dir = DISCOVERY_DIR / "pravda_day_archives"
    if not archive_dir.exists():
        raise SystemExit(
            "data/raw/discovery/pravda_day_archives/ is missing — collect the "
            "day-archive pages first (browser-assisted step, see 01_snapshot.py)."
        )
    urls: dict[str, str] = {}
    for path in sorted(archive_dir.glob("*.html*")):
        day = path.name.split(".")[0]  # YYYY-MM-DD
        raw = (gzip.open(path, "rt", encoding="utf-8").read()
               if path.suffix == ".gz" else path.read_text(encoding="utf-8"))
        soup = BeautifulSoup(raw, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"].split("?")[0]
            if href.startswith("https://www.pravda.com.ua"):
                href = href[len("https://www.pravda.com.ua"):]
            if PRAVDA_NEWS_RE.match(href):
                urls.setdefault("https://www.pravda.com.ua" + href.rstrip("/") + "/", day)
    return urls


def build_url_universe() -> None:
    """Merge all channels into data/raw/discovery/url_universe.csv.

    Columns: outlet, url, channels (|-joined, sorted), sitemap_lastmod.
    Deterministic: sorted by (outlet, url).
    """
    rows: dict[tuple[str, str], dict] = {}

    def add(outlet: str, url: str, channel: str, lastmod: str = "") -> None:
        if outlet == "ukrinform" and not UKRINFORM_RUBRIC_RE.search(url):
            return  # off-topic rubric (world kept for S-world scenario)
        key = (outlet, url)
        row = rows.setdefault(key, {"channels": set(), "lastmod": ""})
        row["channels"].add(channel)
        if lastmod and not row["lastmod"]:
            row["lastmod"] = lastmod

    # -- Ukrinform: recovered weekly sitemaps
    for xml_path in sorted((DISCOVERY_DIR / "ukrinform_sitemaps").glob("*.xml")):
        for loc, lastmod in parse_sitemap_xml(xml_path.read_text(encoding="utf-8")):
            add("ukrinform", loc.strip(), "sitemap", lastmod)

    # -- Ukrinform: v1 inventories (bootstrap channel)
    p0 = json.loads((BOOTSTRAP_DIR / "p0_urls.json").read_text())
    for rec in p0:
        add("ukrinform", rec["url"], "v1_p0")
    csv.field_size_limit(sys.maxsize)
    with open(BOOTSTRAP_DIR / "corpus_fast.csv", newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            add("ukrinform", rec["url"], "v1_corpus")
    recovered = json.loads((BOOTSTRAP_DIR / "recovered_jan_feb_2024.json").read_text())
    for rec in recovered:
        add("ukrinform", rec["url"] if isinstance(rec, dict) else rec, "v1_recovered")

    # -- Suspilne: CDX pages
    cdx_dir = DISCOVERY_DIR / "suspilne_cdx"
    if cdx_dir.exists():
        for page_path in sorted(cdx_dir.glob("*.json")):
            rows_json = json.loads(page_path.read_text())
            for original, _ts in rows_json[1:]:
                url = original.replace("http://", "https://").split("?")[0]
                m = SUSPILNE_ARTICLE_RE.match(url)
                if m:
                    add("suspilne", url.rstrip("/") + "/", "wayback_cdx")

    # -- Suspilne: live sitemap shards (if collected)
    live_dir = DISCOVERY_DIR / "suspilne_sitemaps"
    if live_dir.exists():
        for xml_path in sorted(live_dir.glob("*.xml")):
            for loc, lastmod in parse_sitemap_xml(xml_path.read_text(encoding="utf-8")):
                if SUSPILNE_ARTICLE_RE.match(loc.strip().rstrip("/") + "/"):
                    add("suspilne", loc.strip().rstrip("/") + "/", "sitemap", lastmod)

    # -- Pravda: committed day archives
    if (DISCOVERY_DIR / "pravda_day_archives").exists():
        for url, day in pravda_urls_from_day_archives().items():
            add("pravda", url, "day_archive", day)

    out = DISCOVERY_DIR / "url_universe.csv.gz"
    with gzip.open(out, "wt", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["outlet", "url", "channels", "sitemap_lastmod"])
        for (outlet, url) in sorted(rows):
            row = rows[(outlet, url)]
            w.writerow([outlet, url, "|".join(sorted(row["channels"])), row["lastmod"]])
    counts: dict[str, int] = {}
    for outlet, _ in rows:
        counts[outlet] = counts.get(outlet, 0) + 1
    print(f"url universe written: {out}")
    print(json.dumps(counts, indent=1, sort_keys=True))
