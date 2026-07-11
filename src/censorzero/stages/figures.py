"""figures stage: processed metrics -> site/figures.json + lineage manifest.

site/figures.json is the SINGLE source of truth for the website and the
README. No number is written to HTML or README except through this file.
"""

import json
from pathlib import Path

from .. import PIPELINE_VERSION
from ..canonical import sha256_file, write_json
from ..manifest import raw_shard_hashes, write_lineage
from ..periods import PERIODS

LIMITATIONS = {
    "uk": [
        "Проксі-валідність: оцінка ІМІ — експертна й ручна; наша — лексична й структурна. Збіг вимірюється (Валідація), а не припускається.",
        "Тіла статей узято зі снапшотів Web Archive (стабільні, датовані), бо тижневі мапи сайту за 2023 рік уже недоступні наживо; це навіть відтворюваніше, але покриття архіву неповне — частка непокритих статей публікується.",
        "Правки після публікації невидимі, окрім поля dateModified, яке фіксується.",
        "Суспільне ВИКЛЮЧЕНО з числового порівняння: інструмент видобування джерел не валідовано на ньому золотим стандартом, а середня кількість джерел на статтю тут утричі вища — на довгих репортажах алгоритм over-detect'ить джерела й занулює паркет/баланс (0% тут — артефакт, а не факт). Порівнюваний контроль — «Українська правда» (денний ценз; індексні сторінки за бот-захистом, сирі сторінки закомічено).",
        "Одна людина має конфлікт інтересів і писала codebook; codebook закомічено до розмітки, а LLM-розмітник не бачить періодів.",
        "Вимірюються лише два названі сигнали. Рішення ІМІ могло спиратися на те, що тут не вимірюється; відсутність сигналу не є доказом безпідставності рішення.",
    ],
    "en": [
        "Proxy validity: IMI's assessment is expert and manual; ours is lexical and structural. Agreement is measured (Validation), not assumed.",
        "Article bodies come from Web Archive snapshots (stable, timestamped) because the site's 2023 weekly sitemaps have expired from the live web; this is if anything more reproducible, but archive coverage is incomplete — the uncovered share is published.",
        "Post-publication edits are invisible except via dateModified, which is recorded.",
        "Suspilne is EXCLUDED from the numeric comparison: the source extractor is not gold-validated on it and its average source count per article is three times higher — on long-form reports the extractor over-detects sources and zeroes out parket/balance (0% here is an artifact, not a fact). The comparable control is Ukrainska Pravda (day-census; index pages bot-gated, raw pages committed).",
        "One person holds the conflict of interest and wrote the codebook; the codebook is committed before annotation and the LLM annotator never sees period labels.",
        "Only two named signals are measured. IMI's decision may rest on factors not measurable here; absence of a signal is not proof the decision was unfounded.",
    ],
}

REPO_ROOT = Path(__file__).resolve().parents[3]
INTERIM = REPO_ROOT / "data" / "interim"
PROCESSED = REPO_ROOT / "data" / "processed"
GOLD_REPORT = REPO_ROOT / "data" / "gold" / "report.json"
SITE = REPO_ROOT / "site"

# Decision thresholds from PREREGISTRATION §8.6.
ALPHA = 0.05
H_MEANINGFUL = 0.2


def _verdict(contrasts: dict) -> dict:
    """Apply the preregistered headline decision rule for the parket outcome.

    Contrast fields may be null when coverage is thin (partial collection);
    null is treated as 'not significant' so the verdict degrades to
    'not supported / pending' rather than crashing."""
    def _num(x, default):
        return default if x is None else x

    # Label "parket:P0-P1" has rate_a=P0, rate_b=P1, diff=P0-P1 -> P1>P0 <=> diff<0.
    c01 = contrasts.get("parket:P0-P1", {})
    c12 = contrasts.get("parket:P1-P2", {})
    p1_over_p0 = (_num(c01.get("p_holm"), 1) < ALPHA and _num(c01.get("diff"), 0) < 0
                  and abs(_num(c01.get("cohen_h"), 0)) >= H_MEANINGFUL)
    p1_over_p2 = (_num(c12.get("p_holm"), 1) < ALPHA and _num(c12.get("diff"), 0) > 0
                  and abs(_num(c12.get("cohen_h"), 0)) >= H_MEANINGFUL)
    consistent = bool(p1_over_p0 and p1_over_p2)
    return {
        "implied_pattern_supported": consistent,
        "P1_significantly_above_P0": p1_over_p0,
        "P1_significantly_above_P2": p1_over_p2,
        "rule": "Supported only if P1 standardized parket exceeds BOTH P0 and P2 "
                "(Holm p<0.05, |h|>=0.2). Otherwise: the proxy does not show the "
                "implied pattern.",
    }


def _trend_interpretable(gold: dict | None) -> dict:
    """Preregistered §9 precondition: between-period trends are interpretable
    only if parser recall is stable across periods. If the gold standard shows
    recall drift (>10pp spread or homogeneity rejected), trends are declared
    confounded by parsing and no between-period conclusion is drawn."""
    if not gold:
        return {"status": "pending", "interpretable": None}
    rd = gold.get("recall_drift", {})
    confounded = rd.get("confounded")
    overall = gold.get("overall", {})
    return {
        "status": "evaluated",
        "interpretable": (confounded is False),
        "recall_confounded": confounded,
        "recall_spread_pp": rd.get("recall_spread_pp"),
        "recall_homogeneity_p": rd.get("p_value"),
        "precision": overall.get("precision"),
        "recall": overall.get("recall"),
        "note": "Precision high, recall low and period-dependent: the proxy is "
                "specific but insensitive, and its recall drifts across periods, "
                "so the raw between-period parket trend is confounded by "
                "extraction and is NOT interpreted (preregistration section 9).",
    }


def _gate_controls(diff_in_diff: dict, gold: dict | None) -> dict:
    """A control is compared only if the extraction instrument was validated
    against the blind gold standard on it. Others (e.g. Суспільне, whose long
    narrative format makes the extractor over-generate 'sources' and drive
    parket/balance to a degenerate 0) are marked excluded, not silently shown
    as 0 — repeating v1's 'control is 0 by construction' error would be worse
    than dropping the control."""
    validated = set((gold or {}).get("human_measurement", {}).keys())
    out = {}
    for ctrl, block in diff_in_diff.items():
        if ctrl in validated:
            out[ctrl] = block
        else:
            out[ctrl] = {
                "status": "excluded_instrument_unvalidated",
                "reason": "No blind gold-standard validation of the extractor on "
                          "this outlet; its long-form narrative articles yield a "
                          "much higher source count, a sign the extractor "
                          "over-generates sources here and pushes parket/balance "
                          "to a degenerate 0. Not compared (see limitations).",
            }
    return out


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
        # The logistic-regression companion (metrics.json) is computed by an
        # iterative MLE whose trailing digits vary across platforms' libm/BLAS;
        # it is reported as a robustness companion in data/processed/metrics.json
        # but kept OUT of the byte-exact published artifact. Rates and bootstrap
        # p-values here use only integer counts + fixed-order IEEE arithmetic and
        # are exactly reproducible.
        "logistic_note": "Companion logistic regression is in data/processed/"
                         "metrics.json (not byte-gated: iterative MLE is not "
                         "bit-stable across platforms).",
        "sensitivity": metrics["sensitivity"],
        "diff_in_diff": _gate_controls(metrics["diff_in_diff"], gold),
        "control_coverage": metrics["control_coverage"],
        "gold_standard": gold,
        "trend_interpretable": _trend_interpretable(gold),
        "limitations": LIMITATIONS,
        "verification": {
            "reproduce_command": "uv sync --frozen && make verify",
            "inputs_sha256": raw_shard_hashes(),
        },
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
