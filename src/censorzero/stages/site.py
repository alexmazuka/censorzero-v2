"""site stage: interim articles -> chunked explorer data for the static site.

No monolithic JSON in the browser (v1 shipped a 70 MB file). Explorer data is
written as one compact JSON shard per (outlet, period, month) under
site/explorer/, plus site/explorer/index.json listing the shards and totals,
plus site/explorer/gold.json — every blind-annotated article with its label,
so the public UI can show exactly which articles were assessed and how.
Deterministic ordering throughout.
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

DISPLAY_COLUMNS = ["url", "date_published", "rubric", "title", "sc", "oc", "fc",
                   "nc", "official_focus", "parket", "balance_risk",
                   "gold_label", "gold_military", "sources_json"]


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


def run() -> None:
    df = pd.read_parquet(INTERIM / "articles.parquet")
    gold = _gold_by_url()
    df["gold_label"] = df["url"].map(lambda u: (gold.get(u) or {}).get("label"))
    df["gold_military"] = df["url"].map(
        lambda u: bool((gold.get(u) or {}).get("military", False)))

    EXPLORER.mkdir(parents=True, exist_ok=True)
    for old in EXPLORER.glob("*.json"):
        old.unlink()

    df = df.assign(month=df["date_published"].str.slice(0, 7))
    index = {"shards": [], "totals": {}}

    for (outlet, period, month), part in df.groupby(["outlet", "period", "month"], sort=True):
        part = part.sort_values("url")
        rows = part[DISPLAY_COLUMNS].to_dict(orient="records")
        name = f"{outlet}_{period}_{month}.json"
        write_json(EXPLORER / name, rows)
        index["shards"].append({
            "file": name, "outlet": outlet, "period": period, "month": month,
            "n": len(rows), "n_parket": int(part["parket"].sum()),
            "n_balance": int(part["balance_risk"].sum()),
            "n_gold": int(part["gold_label"].notna().sum()),
        })

    for outlet, part in df.groupby("outlet", sort=True):
        index["totals"][outlet] = {
            "n": int(len(part)),
            "n_parket": int(part["parket"].sum()),
            "n_balance": int(part["balance_risk"].sum()),
            "n_gold": int(part["gold_label"].notna().sum()),
        }
    write_json(EXPLORER / "index.json", index)

    # One compact file with every blind-annotated article (the gold sample is
    # small by design, so this stays a few hundred KB).
    g = df[df["gold_label"].notna()].sort_values(["outlet", "period", "url"])
    gold_rows = g[["outlet", "period"] + DISPLAY_COLUMNS].to_dict(orient="records")
    write_json(EXPLORER / "gold.json", gold_rows)

    print(f"site: {len(index['shards'])} explorer shards + gold.json "
          f"({len(gold_rows)} annotated articles) written")
