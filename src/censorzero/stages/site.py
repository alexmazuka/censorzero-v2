"""site stage: interim articles -> chunked explorer data for the static site.

No monolithic JSON in the browser (v1 shipped a 70 MB file). Explorer data is
written as one compact JSON shard per (outlet, period, month) under
site/explorer/, plus site/explorer/index.json listing the shards and totals.
Deterministic ordering throughout.
"""

import json
from pathlib import Path

import pandas as pd

from ..canonical import write_json

REPO_ROOT = Path(__file__).resolve().parents[3]
INTERIM = REPO_ROOT / "data" / "interim"
EXPLORER = REPO_ROOT / "site" / "explorer"

DISPLAY_COLUMNS = ["url", "date_published", "rubric", "title", "sc", "oc", "fc",
                   "nc", "official_focus", "parket", "balance_risk", "sources_json"]


def run() -> None:
    df = pd.read_parquet(INTERIM / "articles.parquet")
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
        })

    for outlet, part in df.groupby("outlet", sort=True):
        index["totals"][outlet] = {
            "n": int(len(part)),
            "n_parket": int(part["parket"].sum()),
            "n_balance": int(part["balance_risk"].sum()),
        }
    write_json(EXPLORER / "index.json", index)
    print(f"site: {len(index['shards'])} explorer shards written")
