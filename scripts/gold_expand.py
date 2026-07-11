#!/usr/bin/env python3
"""Expand the blind annotation sample into a primary measurement instrument.

Context (logged as a Deviation in PREREGISTRATION.md): the automatic proxy
failed the preregistered §9 recall-stability precondition, so direct blind
annotation becomes the primary between-period measurement. This script draws:
  - Ukrinform: up to TARGET_UKR per period TOTAL (counting already-annotated),
    rubric-proportional within period, excluding already-sampled URLs;
  - Ukrainska Pravda (control): TARGET_UP per period;
  - a reliability set: RELIABILITY existing annotated articles for independent
    re-annotation (inter-annotator kappa).

Outputs (blind: id/title/body only): data/gold/parts2/partNN.jsonl and
relNN.jsonl; updated merged key data/gold/sample_key.csv (id,url,period,
rubric,outlet). Deterministic (seeded).
"""

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from censorzero.canonical import rng  # noqa: E402
from censorzero.config import PRIMARY_RUBRICS, WORLD_RUBRIC  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "data" / "gold"
PARTS2 = GOLD / "parts2"
TARGET_UKR = 400
TARGET_UP = 150
RELIABILITY = 150
PART_SIZE = 55


def aid(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def main() -> int:
    df = pd.read_parquet(REPO / "data" / "interim" / "articles.parquet")
    raw = pd.concat(
        (pd.read_parquet(p) for p in sorted((REPO / "data" / "raw" / "articles").glob("*.parquet"))),
        ignore_index=True,
    )[["url", "body_text"]]
    df = df.merge(raw, on="url", how="left")
    df = df[df["body_text"].notna() & (df["body_text"].str.len() > 100)]

    old_key = list(csv.DictReader(open(GOLD / "sample_key.csv")))
    old_urls = {r["url"] for r in old_key}
    old_by_period: dict[str, int] = {}
    for r in old_key:
        old_by_period[r["period"]] = old_by_period.get(r["period"], 0) + 1

    g = rng(888)
    new_rows = []

    def draw(pool: pd.DataFrame, k: int) -> pd.DataFrame:
        pool = pool.sort_values("url").reset_index(drop=True)
        k = min(k, len(pool))
        idx = sorted(g.choice(len(pool), size=k, replace=False).tolist())
        return pool.iloc[idx]

    # --- Ukrinform top-up, rubric-proportional within each period
    ukr = df[(df.outlet == "ukrinform")
             & (df.rubric.isin([*PRIMARY_RUBRICS, WORLD_RUBRIC]))
             & (~df.url.isin(old_urls))]
    for period in ("P0", "P1", "P2"):
        need = TARGET_UKR - old_by_period.get(period, 0)
        sub = ukr[ukr.period == period]
        if need <= 0 or sub.empty:
            continue
        sizes = sub.rubric.value_counts()
        alloc = {r: max(1, round(need * n / len(sub))) for r, n in sizes.items()}
        for rubric, k in sorted(alloc.items()):
            new_rows.append(draw(sub[sub.rubric == rubric], k))

    # --- UP control
    up = df[(df.outlet == "pravda") & (~df.url.isin(old_urls))]
    for period in ("P0", "P1", "P2"):
        new_rows.append(draw(up[up.period == period], TARGET_UP))

    new = pd.concat(new_rows).drop_duplicates("url").reset_index(drop=True)

    # --- write blind parts
    PARTS2.mkdir(parents=True, exist_ok=True)
    for old in PARTS2.glob("*.jsonl"):
        old.unlink()
    recs = [{"id": aid(r.url), "title": r.title or "", "body": r.body_text}
            for r in new.itertuples()]
    # shuffle so a part never clusters one outlet/period (annotator stays blind
    # to structure); seeded => deterministic
    order = g.permutation(len(recs)).tolist()
    recs = [recs[i] for i in order]
    n_parts = math.ceil(len(recs) / PART_SIZE)
    for i in range(n_parts):
        with open(PARTS2 / f"part{i:02d}.jsonl", "w", encoding="utf-8") as fh:
            for r in recs[i * PART_SIZE:(i + 1) * PART_SIZE]:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- reliability set from already-annotated articles
    ann_ids = [r["id"] for r in csv.DictReader(open(GOLD / "annotations.csv"))]
    ridx = sorted(g.choice(len(ann_ids), size=min(RELIABILITY, len(ann_ids)),
                           replace=False).tolist())
    rel_ids = {ann_ids[i] for i in ridx}
    # bodies for reliability come from the ORIGINAL blind sample file
    orig = {}
    for line in open(GOLD / "sample.jsonl", encoding="utf-8"):
        rec = json.loads(line)
        orig[rec["id"]] = rec
    rel = [orig[i] for i in sorted(rel_ids) if i in orig]
    rel_parts = math.ceil(len(rel) / 50)
    for i in range(rel_parts):
        with open(PARTS2 / f"rel{i}.jsonl", "w", encoding="utf-8") as fh:
            for r in rel[i * 50:(i + 1) * 50]:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- merged key with outlet column
    with open(GOLD / "sample_key.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "url", "period", "rubric", "outlet"])
        for r in old_key:
            w.writerow([r["id"], r["url"], r["period"], r["rubric"],
                        r.get("outlet", "ukrinform")])
        for row in new.sort_values("url").itertuples():
            w.writerow([aid(row.url), row.url, row.period, row.rubric, row.outlet])

    print(f"new blind articles: {len(recs)} in {n_parts} parts; "
          f"reliability: {len(rel)} in {rel_parts} parts")
    print(new.groupby(["outlet", "period"]).size())
    return 0


if __name__ == "__main__":
    sys.exit(main())
