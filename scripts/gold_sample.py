#!/usr/bin/env python3
"""Draw the blinded gold-standard sample (PREREGISTRATION.md section 9).

Stratified by period x rubric proportional to Ukrinform cell sizes, >= 300
articles, fixed seed. Writes data/gold/sample.jsonl with ONLY id/title/body
(blind: no url, date, rubric, period, or classifier output). The id->article
key stays in data/gold/sample_key.csv (not shown to the annotator).

Run once, after the snapshot is frozen. Deterministic given the snapshot.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from censorzero.canonical import rng  # noqa: E402
from censorzero.config import OUTLET_UKRINFORM, PRIMARY_RUBRICS, WORLD_RUBRIC  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERIM = REPO_ROOT / "data" / "interim" / "articles.parquet"
GOLD = REPO_ROOT / "data" / "gold"
TARGET = 320  # >= 300, round for clean proportional allocation


def main() -> int:
    df = pd.read_parquet(INTERIM)
    df = df[(df["outlet"] == OUTLET_UKRINFORM)
            & (df["rubric"].isin([*PRIMARY_RUBRICS, WORLD_RUBRIC]))].copy()
    df["body"] = df["title"].fillna("")  # placeholder; real body added below
    # We need body_text — it is not in interim (kept in raw). Re-attach from raw.
    raw = pd.concat(
        (pd.read_parquet(p) for p in sorted((REPO_ROOT / "data" / "raw" / "articles").glob("ukrinform_*.parquet"))),
        ignore_index=True,
    )[["url", "body_text"]]
    df = df.merge(raw, on="url", how="left")

    # proportional allocation over period x rubric
    df["cell"] = df["period"] + "|" + df["rubric"]
    sizes = df["cell"].value_counts()
    total = len(df)
    alloc = {cell: max(1, round(TARGET * n / total)) for cell, n in sizes.items()}

    g = rng(777)  # sampling seed, distinct from bootstrap
    picks = []
    for cell, k in sorted(alloc.items()):
        pool = df[df["cell"] == cell].sort_values("url").reset_index(drop=True)
        k = min(k, len(pool))
        idx = sorted(g.choice(len(pool), size=k, replace=False).tolist())
        picks.append(pool.iloc[idx])
    sample = pd.concat(picks).sort_values("url").reset_index(drop=True)

    GOLD.mkdir(parents=True, exist_ok=True)
    with open(GOLD / "sample.jsonl", "w", encoding="utf-8") as blind, \
         open(GOLD / "sample_key.csv", "w", newline="", encoding="utf-8") as keyf:
        kw = csv.writer(keyf)
        kw.writerow(["id", "url", "period", "rubric"])
        for row in sample.itertuples(index=False):
            aid = hashlib.sha256(row.url.encode()).hexdigest()[:16]
            blind.write(json.dumps(
                {"id": aid, "title": row.title or "", "body": row.body_text or ""},
                ensure_ascii=False) + "\n")
            kw.writerow([aid, row.url, row.period, row.rubric])
    print(f"gold sample: {len(sample)} articles across {len(alloc)} cells "
          f"-> data/gold/sample.jsonl (+ sample_key.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
