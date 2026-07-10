"""figures stage: processed metrics -> site/figures.json + lineage manifest.

site/figures.json is the SINGLE source of truth for the website and the
README. No number is written to HTML or README except through this file.
"""

import json
from pathlib import Path

from .. import PIPELINE_VERSION
from ..canonical import sha256_file, write_json
from ..manifest import write_lineage
from ..periods import PERIODS

REPO_ROOT = Path(__file__).resolve().parents[3]
INTERIM = REPO_ROOT / "data" / "interim"
PROCESSED = REPO_ROOT / "data" / "processed"
GOLD_REPORT = REPO_ROOT / "data" / "gold" / "report.json"
SITE = REPO_ROOT / "site"

# Decision thresholds from PREREGISTRATION §8.6.
ALPHA = 0.05
H_MEANINGFUL = 0.2


def _verdict(contrasts: dict) -> dict:
    """Apply the preregistered headline decision rule for the parket outcome."""
    def sig_up(label):
        c = contrasts.get(label, {})
        return c.get("p_holm", 1) < ALPHA and c.get("diff", 0) > 0 and abs(c.get("cohen_h", 0)) >= H_MEANINGFUL

    p1_gt_p0 = sig_up("parket:P0-P1")           # P1 > P0 means diff (P0-P1) < 0
    # our contrast label "parket:P0-P1" has rate_a=P0, rate_b=P1, diff=P0-P1.
    c01 = contrasts.get("parket:P0-P1", {})
    c12 = contrasts.get("parket:P1-P2", {})
    p1_over_p0 = (c01.get("p_holm", 1) < ALPHA and c01.get("diff", 0) < 0
                  and abs(c01.get("cohen_h", 0)) >= H_MEANINGFUL)
    p1_over_p2 = (c12.get("p_holm", 1) < ALPHA and c12.get("diff", 0) > 0
                  and abs(c12.get("cohen_h", 0)) >= H_MEANINGFUL)
    consistent = bool(p1_over_p0 and p1_over_p2)
    return {
        "implied_pattern_supported": consistent,
        "P1_significantly_above_P0": p1_over_p0,
        "P1_significantly_above_P2": p1_over_p2,
        "rule": "Supported only if P1 standardized parket exceeds BOTH P0 and P2 "
                "(Holm p<0.05, |h|>=0.2). Otherwise: the proxy does not show the "
                "implied pattern.",
    }


def run() -> None:
    metrics = json.loads((PROCESSED / "metrics.json").read_text())
    counts = json.loads((INTERIM / "counts.json").read_text())
    gold = json.loads(GOLD_REPORT.read_text()) if GOLD_REPORT.exists() else None

    figures = {
        "pipeline_version": PIPELINE_VERSION,
        "periods": [
            {"key": p.key, "start": p.start.isoformat(), "end": p.end.isoformat(),
             "label_ua": p.label_ua, "label_en": p.label_en}
            for p in PERIODS
        ],
        "coverage": counts,
        "standard_weights": metrics["standard_weights"],
        "rates": metrics["rates"],
        "contrasts": metrics["contrasts"],
        "logistic": metrics["logistic"],
        "sensitivity": metrics["sensitivity"],
        "diff_in_diff": metrics["diff_in_diff"],
        "control_coverage": metrics["control_coverage"],
        "gold_standard": gold,
        "verdict": _verdict(metrics["contrasts"]),
        "conflict_of_interest": (
            "The author of this study led Ukrinform during period P1. See "
            "PREREGISTRATION.md section 1. Reproducibility, not the author's "
            "word, is the evidence: every number here is regenerated from the "
            "committed raw snapshot and checked bit-for-bit in CI."
        ),
        "notes": {
            "absolute_levels": "Uninterpretable (depend on extractor recall). "
                               "Only between-period/outlet contrasts are read, "
                               "conditional on recall stability (gold_standard).",
            "imi_threshold": "IMI publishes no numeric parket/balance threshold; "
                             "the parket metric is this study's own proxy.",
        },
    }

    SITE.mkdir(parents=True, exist_ok=True)
    write_json(SITE / "figures.json", figures)

    # Lineage: hash every committed output the pipeline produced.
    outputs = {}
    for rel in ["data/interim/articles.parquet", "data/interim/counts.json",
                "data/processed/metrics.json", "site/figures.json"]:
        p = REPO_ROOT / rel
        if p.exists():
            outputs[rel] = sha256_file(p)
    write_lineage(outputs)
    print("figures: site/figures.json + data/manifests/lineage.json written")
