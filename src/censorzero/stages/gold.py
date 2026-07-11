"""gold stage: classifier vs blind human/LLM annotation -> PR/F1 report.

Reads the committed annotations (data/gold/annotations.csv) and the sample key,
joins the classifier's parket flag from interim, and writes data/gold/report.json:
confusion matrix, precision/recall/F1 overall and per period, a recall-drift
test across periods, and the sc==0 breakdown. If annotations are absent the
stage is a no-op (figures.json then marks the gold standard as pending).
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, norm

from ..canonical import write_json

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD = REPO_ROOT / "data" / "gold"
INTERIM = REPO_ROOT / "data" / "interim" / "articles.parquet"


def _wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return float("nan"), float("nan")
    z = 1.959964
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def _cohen_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(max(0, min(1, p1)))) - 2 * math.asin(math.sqrt(max(0, min(1, p2))))


def _human_measurement(df: pd.DataFrame) -> dict:
    """Direct blind-annotation measurement per outlet x period.

    This is the PRIMARY between-period instrument after the automatic proxy
    failed the §9 recall-stability precondition (see PREREGISTRATION
    Deviations). Military bulletins are excluded, matching the corpus analysis.
    """
    out: dict = {}
    main = df[~df["military"]]
    for outlet, sub in main.groupby("outlet"):
        per = {}
        for pk in ("P0", "P1", "P2"):
            s = sub[sub.period == pk]
            n, k = len(s), int(s.gold_parket.sum())
            lo, hi = _wilson(k, n)
            per[pk] = {"n": n, "k": k,
                       "rate": (k / n if n else float("nan")),
                       "ci_low": lo, "ci_high": hi}
        block: dict = {"per_period": per}
        counts = [(per[p]["k"], per[p]["n"] - per[p]["k"]) for p in ("P0", "P1", "P2")
                  if per[p]["n"] > 0]
        if len(counts) == 3 and all(a + b > 0 for a, b in counts):
            chi2, p, _, _ = chi2_contingency(np.array(counts))
            block["homogeneity"] = {"chi2": float(chi2), "p_value": float(p)}
            pairs = [("P0", "P1"), ("P1", "P2"), ("P0", "P2")]
            praw = []
            pairwise = {}
            for a, b in pairs:
                pa, pb = per[a], per[b]
                p1, p2 = pa["rate"], pb["rate"]
                n1, n2 = pa["n"], pb["n"]
                pool = (pa["k"] + pb["k"]) / (n1 + n2)
                se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
                z = (p1 - p2) / se if se else float("nan")
                pv = float(2 * (1 - norm.cdf(abs(z)))) if se else float("nan")
                h = _cohen_h(p1, p2)
                hse = math.sqrt(1 / n1 + 1 / n2)
                pairwise[f"{a}-{b}"] = {
                    "diff": p1 - p2, "h": h,
                    "h_ci_low": h - 1.959964 * hse, "h_ci_high": h + 1.959964 * hse,
                    "p_raw": pv,
                }
                praw.append((f"{a}-{b}", pv))
            # Holm over the 3 pairwise tests
            m = len(praw)
            running = 0.0
            for rank, (key, pv) in enumerate(sorted(praw, key=lambda x: x[1])):
                adj = min(1.0, (m - rank) * pv)
                running = max(running, adj)
                pairwise[key]["p_holm"] = running
            block["pairwise"] = pairwise
            # ~80%-power minimum detectable difference for the P0-P1 sizes
            n1, n2 = per["P0"]["n"], per["P1"]["n"]
            pbar = (per["P0"]["k"] + per["P1"]["k"]) / max(1, n1 + n2)
            block["min_detectable_diff_pp"] = float(
                100 * 2.8 * math.sqrt(pbar * (1 - pbar) * (1 / max(1, n1) + 1 / max(1, n2))))
        out[str(outlet)] = block
    return out


def _kappa(pairs: list[tuple[str, str]]) -> dict:
    """Cohen's kappa for two binary label sequences."""
    n = len(pairs)
    if n == 0:
        return {"n_overlap": 0}
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    pa1 = sum(1 for a, _ in pairs if a == "parket") / n
    pb1 = sum(1 for _, b in pairs if b == "parket") / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return {"n_overlap": n, "agreement": po, "kappa": kappa}


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
    # period comes from the sample key; take only classifier fields from interim
    # to avoid a period_x/period_y merge collision.
    interim = pd.read_parquet(INTERIM)[["url", "parket", "sc"]]

    df = ann.merge(key, on="id", how="inner").merge(interim, on="url", how="left")
    df["gold_parket"] = df["label"].str.strip().eq("parket")
    df["pred_parket"] = df["parket"].fillna(False).astype(bool)
    df["military"] = df.get("military_bulletin", "").astype(str).str.lower().isin(
        ("true", "1", "yes"))
    if "outlet" not in df.columns:
        df["outlet"] = "ukrinform"
    df["outlet"] = df["outlet"].fillna("ukrinform")

    # Classifier validation runs on the treatment outlet (the classifier is
    # identical for controls; PR/F1 is defined against the Ukrinform gold set).
    ukr = df[df.outlet == "ukrinform"]
    # Primary analysis excludes military bulletins (matches the corpus analysis).
    main = ukr[~ukr["military"]]

    def confusion(sub: pd.DataFrame) -> dict:
        tp = int(((sub.pred_parket) & (sub.gold_parket)).sum())
        fp = int(((sub.pred_parket) & (~sub.gold_parket)).sum())
        fn = int(((~sub.pred_parket) & (sub.gold_parket)).sum())
        tn = int(((~sub.pred_parket) & (~sub.gold_parket)).sum())
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, **_prf(tp, fp, fn), "n": len(sub)}

    report = {
        "n_annotated": int(len(df)),
        "n_annotated_by_outlet": {str(o): int(n) for o, n in
                                  df.groupby("outlet").size().items()},
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

    # --- Direct blind measurement (primary between-period instrument after
    # the §9 stop-rule; see PREREGISTRATION Deviations).
    report["human_measurement"] = _human_measurement(df)

    # --- Inter-annotator reliability (independent re-annotation of a subsample)
    rel_path = GOLD / "reliability.csv"
    if rel_path.exists():
        rel = pd.read_csv(rel_path, dtype=str)
        base = df.set_index("id")["label"].to_dict()
        pairs = [(base[r.id].strip(), r.label.strip())
                 for r in rel.itertuples() if r.id in base]
        report["reliability"] = _kappa(pairs)

    # --- Author (human) validation of a blind subsample, if provided
    hv_path = GOLD / "human_validation.csv"
    if hv_path.exists():
        hv = pd.read_csv(hv_path, dtype=str)
        hv = hv[hv["label"].astype(str).str.strip().isin(["parket", "non_parket"])]
        base = df.set_index("id")["label"].to_dict()
        pairs = [(base[r.id].strip(), r.label.strip())
                 for r in hv.itertuples() if r.id in base]
        report["human_validation"] = _kappa(pairs)

    write_json(GOLD / "report.json", report)
    o = report["overall"]
    print(f"gold: n={report['n_annotated']} precision={o['precision']:.3f} "
          f"recall={o['recall']:.3f} f1={o['f1']:.3f}")
