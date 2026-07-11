"""site stage: interim articles -> browsable data for the static site.

Two kinds of output, both designed for a non-technical visitor:

  site/explorer/browse/{outlet}.json
      Every article of that outlet, ALL periods, with only the fields needed
      to browse and search: date, title, url, rubric, period, and a plain
      status for the algorithm and (if present) the blind human annotation.
      One file per outlet (not per month) so the browser fetches it once and
      then filters/searches instantly with no further network calls.

  site/explorer/gold.json
      Every blind-annotated article with its human label — "which articles
      did we actually check by hand, and what did we find" in one small file.

  site/explorer/index.json
      Just counts (per outlet, per outlet+period) for the summary view.

No monolithic 70 MB blob (v1's mistake) and no per-month fragmentation that
forces a user to guess which of 50 files to open (v2's earlier mistake).
"""

import csv
import json
from pathlib import Path

import pandas as pd

from ..canonical import write_json

REPO_ROOT = Path(__file__).resolve().parents[3]
INTERIM = REPO_ROOT / "data" / "interim"
GOLD = REPO_ROOT / "data" / "gold"
EXPLORER = REPO_ROOT / "site" / "explorer"
BROWSE = EXPLORER / "browse"

# Short keys keep the browse files small; gzip (served automatically by
# GitHub Pages) collapses the repetition further.
BROWSE_COLUMNS = {
    "url": "u", "date_published": "d", "title": "t", "rubric": "r",
    "period": "p", "algo": "a", "gold": "g",
}


def _gold_by_url() -> dict[str, dict]:
    """url -> {label, military} from committed blind annotations."""
    ann_path = GOLD / "annotations.csv"
    key_path = GOLD / "sample_key.csv"
    if not (ann_path.exists() and key_path.exists()):
        return {}
    key = {r["id"]: r for r in csv.DictReader(open(key_path, encoding="utf-8"))}
    out: dict[str, dict] = {}
    for r in csv.DictReader(open(ann_path, encoding="utf-8")):
        k = key.get(r["id"])
        label = (r.get("label") or "").strip()
        if not k or label not in ("parket", "non_parket"):
            continue
        out[k["url"]] = {
            "label": label,
            "military": (r.get("military_bulletin") or "").strip().lower()
            in ("true", "1", "yes"),
        }
    return out


def _algo_status(row) -> str | None:
    if row.parket:
        return "parket"
    if row.balance_risk:
        return "balance"
    return None


def _gold_status(row) -> str | None:
    if row.gold_label is None:
        return None
    if row.gold_military:
        return "military"
    return row.gold_label  # "parket" | "non_parket"


def run() -> None:
    df = pd.read_parquet(INTERIM / "articles.parquet")
    gold = _gold_by_url()
    df["gold_label"] = df["url"].map(lambda u: (gold.get(u) or {}).get("label"))
    df["gold_military"] = df["url"].map(
        lambda u: bool((gold.get(u) or {}).get("military", False)))

    EXPLORER.mkdir(parents=True, exist_ok=True)
    BROWSE.mkdir(parents=True, exist_ok=True)
    for old in EXPLORER.glob("*.json"):
        old.unlink()
    for old in BROWSE.glob("*.json"):
        old.unlink()

    df["algo"] = [_algo_status(r) for r in df.itertuples()]
    df["gold"] = [_gold_status(r) for r in df.itertuples()]

    index = {"by_outlet": {}, "by_outlet_period": {}}

    for outlet, part in df.groupby("outlet", sort=True):
        part = part.sort_values("date_published", ascending=False)
        rows = [
            {short: getattr(r, long) for long, short in BROWSE_COLUMNS.items()}
            for r in part.itertuples()
        ]
        write_json(BROWSE / f"{outlet}.json", rows)
        index["by_outlet"][outlet] = {
            "n": int(len(part)),
            "n_parket": int((part["algo"] == "parket").sum()),
            "n_balance": int((part["algo"] == "balance").sum()),
            "n_gold": int(part["gold_label"].notna().sum()),
        }
        for period, sub in part.groupby("period"):
            index["by_outlet_period"].setdefault(outlet, {})[period] = {
                "n": int(len(sub)),
                "n_parket": int((sub["algo"] == "parket").sum()),
                "n_balance": int((sub["algo"] == "balance").sum()),
                "n_gold": int(sub["gold_label"].notna().sum()),
            }
    write_json(EXPLORER / "index.json", index)

    # Every blind-annotated article with its human label, small by design.
    g = df[df["gold_label"].notna()].sort_values(["outlet", "period", "url"])
    gold_cols = ["outlet", "period", "url", "date_published", "title", "rubric",
                 "algo", "gold"]
    gold_rows = g[gold_cols].to_dict(orient="records")
    write_json(EXPLORER / "gold.json", gold_rows)

    print(f"site: browse/{{outlet}}.json x{len(index['by_outlet'])} "
          f"+ gold.json ({len(gold_rows)} annotated articles) written")
