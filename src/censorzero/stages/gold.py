"""gold stage: classifier vs blind human/LLM annotation -> PR/F1 report.

Reads the committed annotations (data/gold/annotations.csv) and the sample key,
joins the classifier's parket flag from interim, and writes data/gold/report.json:
confusion matrix, precision/recall/F1 overall and per period, a recall-drift
test across periods, and the sc==0 breakdown. If annotations are absent the
stage is a no-op (figures.json then marks the gold standard as pending).
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from ..canonical import write_json

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD = REPO_ROOT / "data" / "gold"
INTERIM = REPO_ROOT / "data" / "interim" / "articles.parquet"


def _prf(tp: int, fp: int, fn: int) -> dict:
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * prec * rec / (prec + rec)
          if prec == prec and rec == rec and (prec + rec) else float("nan"))
    return {"precision": prec, "recall": rec, "f1": f1}


def run() -> None:
    ann_path = GOLD / "annotations.csv"
    key_path = GOLD / "sample_key.csv"
    if not (ann_path.exists() and key_path.exists()):
        print("gold: no annotations yet — skipping (figures will mark pending)")
        return

    ann = pd.read_csv(ann_path, dtype=str)
    key = pd.read_csv(key_path, dtype=str)
    interim = pd.read_parquet(INTERIM)[["url", "period", "parket", "sc"]]

    df = ann.merge(key, on="id", how="inner").merge(interim, on="url", how="left")
    df["gold_parket"] = df["label"].str.strip().eq("parket")
    df["pred_parket"] = df["parket"].astype(bool)
    df["military"] = df.get("military_bulletin", "").astype(str).str.lower().isin(
        ("true", "1", "yes"))

    # Primary analysis excludes military bulletins (matches the corpus analysis).
    main = df[~df["military"]]

    def confusion(sub: pd.DataFrame) -> dict:
        tp = int(((sub.pred_parket) & (sub.gold_parket)).sum())
        fp = int(((sub.pred_parket) & (~sub.gold_parket)).sum())
        fn = int(((~sub.pred_parket) & (sub.gold_parket)).sum())
        tn = int(((~sub.pred_parket) & (~sub.gold_parket)).sum())
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, **_prf(tp, fp, fn), "n": len(sub)}

    report = {
        "n_annotated": int(len(df)),
        "n_military_bulletin": int(df["military"].sum()),
        "n_uncertain": int(df.get("uncertain", pd.Series(dtype=str))
                           .astype(str).str.lower().isin(("true", "1", "yes")).sum()),
        "overall": confusion(main),
        "by_period": {pk: confusion(main[main.period == pk])
                      for pk in sorted(main["period"].dropna().unique())},
        "sc0_breakdown": {
            "gold_parket_with_sc0": int(((main.gold_parket) & (main.sc == 0)).sum()),
            "note": "articles a human calls parket but the extractor found 0 sources "
                    "(extraction misses); parket by definition requires sc==1, so "
                    "these are recall losses, not false positives.",
        },
    }

    # Recall-drift test across periods (PREREGISTRATION §9 precondition).
    # Contingency: period x (classifier correct on gold-parket vs missed).
    rows = []
    for pk, sub in main[main.gold_parket].groupby("period"):
        hit = int((sub.pred_parket).sum())
        miss = int((~sub.pred_parket).sum())
        rows.append((pk, hit, miss))
    recall_drift = {"per_period": {pk: {"hit": h, "miss": m} for pk, h, m in rows}}
    table = np.array([[h, m] for _, h, m in rows])
    if table.shape[0] >= 2 and table.sum() > 0 and (table.sum(axis=1) > 0).all():
        try:
            chi2, p, _, _ = chi2_contingency(table)
            recalls = [h / (h + m) if (h + m) else float("nan") for _, h, m in rows]
            spread = (max(recalls) - min(recalls)) if recalls else float("nan")
            recall_drift.update({
                "chi2": float(chi2), "p_value": float(p),
                "recall_spread_pp": float(spread * 100),
                "confounded": bool(p < 0.05 or spread > 0.10),
            })
        except ValueError:
            recall_drift["status"] = "insufficient_data"
    else:
        recall_drift["status"] = "insufficient_data"
    report["recall_drift"] = recall_drift

    write_json(GOLD / "report.json", report)
    o = report["overall"]
    print(f"gold: n={report['n_annotated']} precision={o['precision']:.3f} "
          f"recall={o['recall']:.3f} f1={o['f1']:.3f}")
