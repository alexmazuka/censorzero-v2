#!/usr/bin/env python3
"""Merge parts2 annotation CSVs into the committed gold inputs.

- part*_annot.csv -> appended to data/gold/annotations.csv (existing rows win;
  every id must exist in sample_key.csv)
- rel*_annot.csv  -> data/gold/reliability.csv (independent re-annotation)

Also emits data/gold/human_validation_blank.csv — a 60-article blind packet
for the author's validation pass (id,title,body,label-empty). Deterministic.
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from censorzero.canonical import rng  # noqa: E402

GOLD = Path(__file__).resolve().parents[1] / "data" / "gold"
FIELDS = ["id", "label", "military_bulletin", "uncertain", "note"]


def read_csvs(pattern: str) -> list[dict]:
    rows = []
    for p in sorted((GOLD / "parts2").glob(pattern)):
        with open(p, newline="", encoding="utf-8") as fh:
            rows.extend(csv.DictReader(fh))
    return rows


def main() -> int:
    key_ids = {r["id"] for r in csv.DictReader(open(GOLD / "sample_key.csv"))}
    existing = list(csv.DictReader(open(GOLD / "annotations.csv")))
    seen = {r["id"] for r in existing}

    added = skipped = 0
    new_rows = []
    for r in read_csvs("part*_annot.csv"):
        rid = (r.get("id") or "").strip()
        if not rid or rid in seen or rid not in key_ids:
            skipped += 1
            continue
        if r.get("label", "").strip() not in ("parket", "non_parket"):
            skipped += 1
            continue
        seen.add(rid)
        new_rows.append({k: (r.get(k) or "").strip() for k in FIELDS})
        added += 1

    with open(GOLD / "annotations.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in FIELDS})
        for r in sorted(new_rows, key=lambda x: x["id"]):
            w.writerow(r)

    rel = [{"id": r["id"].strip(), "label": r["label"].strip()}
           for r in read_csvs("rel*_annot.csv")
           if r.get("label", "").strip() in ("parket", "non_parket")]
    with open(GOLD / "reliability.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "label"])
        w.writeheader()
        for r in sorted(rel, key=lambda x: x["id"]):
            w.writerow(r)

    # --- author's validation packet: 60 annotated articles, blind
    bodies = {}
    for fname in ("sample.jsonl",):
        for line in open(GOLD / fname, encoding="utf-8"):
            rec = json.loads(line)
            bodies[rec["id"]] = rec
    for p in sorted((GOLD / "parts2").glob("part*.jsonl")):
        for line in open(p, encoding="utf-8"):
            rec = json.loads(line)
            bodies[rec["id"]] = rec
    all_ann = existing + new_rows
    ann_ids = sorted({r["id"] for r in all_ann if r["id"] in bodies})
    g = rng(999)
    pick = sorted(g.choice(len(ann_ids), size=min(60, len(ann_ids)),
                           replace=False).tolist())
    with open(GOLD / "human_validation_blank.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "title", "body", "label"])
        for i in pick:
            rec = bodies[ann_ids[i]]
            w.writerow([rec["id"], rec["title"], rec["body"], ""])

    print(f"annotations: +{added} (skipped {skipped}) -> total {len(existing) + added}")
    print(f"reliability: {len(rel)} rows")
    print("validation packet: data/gold/human_validation_blank.csv (60 articles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
