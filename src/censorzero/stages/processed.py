"""processed stage: interim articles -> aggregated metrics + statistics.

Pure function over data/interim/articles.parquet. Writes:
  data/processed/metrics.json

Contents (PREREGISTRATION.md section 8):
  - standard rubric weights (pooled 3-period Ukrinform distribution),
  - per-period standardized + crude parket/balance rates,
  - the full sensitivity grid (point estimates, for the live dashboard),
  - primary contrasts with Cohen's h + bootstrap CI + Holm-adjusted p,
  - logistic-regression companion (parket ~ period + rubric),
  - descriptive difference-in-differences vs each usable control.
"""

from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config
from ..canonical import write_json
from ..periods import PERIODS
from ..stats import contrast, crude_rate, direct_standardized_rate, holm

REPO_ROOT = Path(__file__).resolve().parents[3]
INTERIM = REPO_ROOT / "data" / "interim"
PROCESSED = REPO_ROOT / "data" / "processed"

PERIOD_KEYS = [p.key for p in PERIODS]
CONTRAST_PAIRS = [("P0", "P1"), ("P1", "P2"), ("P0", "P2")]


def _scenario_flag(df: pd.DataFrame, outcome: str, sc_threshold: int, require_focus: bool) -> np.ndarray:
    """Recompute a parket/balance boolean per row under sensitivity settings."""
    focus_ok = df["official_focus"].to_numpy() if require_focus else np.ones(len(df), bool)
    if outcome == "parket":
        flag = focus_ok & (df["sc"].to_numpy() >= 1) & (df["sc"].to_numpy() <= sc_threshold) \
            & (df["oc"].to_numpy() == df["sc"].to_numpy()) & (df["nc"].to_numpy() == 0)
    else:  # balance
        flag = focus_ok & (df["oc"].to_numpy() >= 1) & (df["nc"].to_numpy() == 0)
    return flag.astype(int)


def _ukr_universe(df: pd.DataFrame, rubric_universe: str, ato: str) -> pd.DataFrame:
    rubrics = list(config.PRIMARY_RUBRICS)
    if rubric_universe == "plus_world":
        rubrics = rubrics + [config.WORLD_RUBRIC]
    sub = df[(df["outlet"] == config.OUTLET_UKRINFORM) & (df["rubric"].isin(rubrics))]
    if ato == "excluded":
        sub = sub[sub["rubric"] != config.ATO_RUBRIC]
    return sub


def _standard_weights(ukr: pd.DataFrame) -> dict[str, float]:
    """Pooled 3-period rubric counts as standardization weights."""
    counts = ukr.groupby("rubric").size()
    return {r: float(n) for r, n in counts.items()}


def _flags_by_rubric(df: pd.DataFrame, flag: np.ndarray, period: str) -> dict[str, np.ndarray]:
    mask = (df["period"] == period).to_numpy()
    out: dict[str, np.ndarray] = {}
    rubrics = df["rubric"].to_numpy()
    for r in np.unique(rubrics[mask]):
        out[str(r)] = flag[mask & (rubrics == r)]
    return out


def _logit_period_effect(ukr: pd.DataFrame, flag_col: str) -> dict:
    """Logistic regression outcome ~ C(period) + C(rubric); report period ORs."""
    import statsmodels.formula.api as smf

    d = ukr.copy()
    d["y"] = d[flag_col].astype(int)
    d = d[["y", "period", "rubric"]]
    # need variation
    if d["y"].nunique() < 2 or d["period"].nunique() < 2:
        return {"status": "insufficient_variation"}
    model = smf.logit("y ~ C(period, Treatment('P0')) + C(rubric)", data=d).fit(disp=0)
    out = {"status": "ok", "n": int(len(d)), "period_terms": {}}
    for name in model.params.index:
        if name.startswith("C(period"):
            key = name.split("T.")[-1].rstrip("]")
            out["period_terms"][key] = {
                "log_odds": float(model.params[name]),
                "odds_ratio": float(np.exp(model.params[name])),
                "p_value": float(model.pvalues[name]),
                "ci_low_or": float(np.exp(model.conf_int().loc[name, 0])),
                "ci_high_or": float(np.exp(model.conf_int().loc[name, 1])),
            }
    return out


def _rates_block(df: pd.DataFrame, weights: dict[str, float]) -> dict:
    block = {}
    for outcome in ("parket", "balance"):
        flag = _scenario_flag(df, outcome, sc_threshold=1, require_focus=True)
        per_period = {}
        for pk in PERIOD_KEYS:
            pmask = (df["period"] == pk).to_numpy()
            fbr = _flags_by_rubric(df, flag, pk)
            per_period[pk] = {
                "n": int(pmask.sum()),
                "n_flagged": int(flag[pmask].sum()),
                "crude": crude_rate(flag[pmask]) if pmask.sum() else float("nan"),
                "standardized": direct_standardized_rate(fbr, weights),
            }
        block[outcome] = per_period
    return block


def run(n_boot: int | None = None) -> None:
    import os

    n_boot = n_boot or int(os.environ.get("CENSORZERO_NBOOT", "10000"))
    df = pd.read_parquet(INTERIM / "articles.parquet")

    ukr_primary = _ukr_universe(df, "primary7", "excluded")
    weights = _standard_weights(ukr_primary)

    result: dict = {
        "n_boot": n_boot,
        "standard_weights": dict(sorted(weights.items())),
        "primary": {"scenario": "sc1_focus_atoExcluded_primary7_direct"},
        "rates": _rates_block(ukr_primary, weights),
        "contrasts": {},
        "logistic": {},
        "sensitivity": {},
        "diff_in_diff": {},
        "control_coverage": {},
    }

    # --- primary contrasts (6 = 2 outcomes x 3 period pairs), Holm across all
    all_contrasts = []
    seed = 100
    for outcome in ("parket", "balance"):
        flag = _scenario_flag(ukr_primary, outcome, 1, True)
        for a, b in CONTRAST_PAIRS:
            cr = contrast(
                f"{outcome}:{a}-{b}",
                _flags_by_rubric(ukr_primary, flag, a),
                _flags_by_rubric(ukr_primary, flag, b),
                weights, seed_offset=seed, n_boot=n_boot,
            )
            seed += 1
            all_contrasts.append(cr)
    holm(all_contrasts)
    for cr in all_contrasts:
        result["contrasts"][cr.label] = {
            "rate_a": cr.rate_a, "rate_b": cr.rate_b, "diff": cr.diff,
            "cohen_h": cr.h, "h_ci_low": cr.h_ci_low, "h_ci_high": cr.h_ci_high,
            "p_raw": cr.p_raw, "p_holm": cr.p_holm,
        }

    # --- logistic companion
    for outcome, col in (("parket", "parket"), ("balance", "balance_risk")):
        result["logistic"][outcome] = _logit_period_effect(ukr_primary, col)

    # --- sensitivity grid (point estimates only, for the live dashboard)
    for sc_thr, req_focus, ato, universe, std in product(
        config.SENSITIVITY["sc_threshold"], config.SENSITIVITY["require_focus"],
        config.SENSITIVITY["ato"], config.SENSITIVITY["rubric_universe"],
        config.SENSITIVITY["standardization"],
    ):
        sub = _ukr_universe(df, universe, ato)
        w = _standard_weights(sub)
        cell = {}
        for outcome in ("parket", "balance"):
            flag = _scenario_flag(sub, outcome, sc_thr, req_focus)
            per_period = {}
            for pk in PERIOD_KEYS:
                pmask = (sub["period"] == pk).to_numpy()
                if std == "crude":
                    rate = crude_rate(flag[pmask]) if pmask.sum() else float("nan")
                else:
                    rate = direct_standardized_rate(_flags_by_rubric(sub, flag, pk), w)
                per_period[pk] = {"n": int(pmask.sum()), "rate": rate}
            cell[outcome] = per_period
        key = f"sc{sc_thr}_focus{int(req_focus)}_ato{ato}_{universe}_{std}"
        result["sensitivity"][key] = cell

    # --- difference-in-differences vs controls (descriptive)
    for ctrl in config.CONTROL_OUTLETS:
        cdf = df[df["outlet"] == ctrl]
        coverage = {pk: int((cdf["period"] == pk).sum()) for pk in PERIOD_KEYS}
        result["control_coverage"][ctrl] = coverage
        # usable if all three periods have data (rule in PREREGISTRATION §6)
        usable = all(coverage[pk] > 0 for pk in PERIOD_KEYS)
        if not usable:
            result["diff_in_diff"][ctrl] = {"status": "insufficient_coverage",
                                            "coverage": coverage}
            continue
        did = {"status": "descriptive"}
        for outcome in ("parket", "balance"):
            uflag = _scenario_flag(ukr_primary, outcome, 1, True)
            cflag = _scenario_flag(cdf, outcome, 1, True)
            u = {pk: crude_rate(uflag[(ukr_primary["period"] == pk).to_numpy()]) for pk in PERIOD_KEYS}
            c = {pk: crude_rate(cflag[(cdf["period"] == pk).to_numpy()]) for pk in PERIOD_KEYS}
            did[outcome] = {
                "ukrinform": u, "control": c,
                "did_P0_P1": (u["P1"] - u["P0"]) - (c["P1"] - c["P0"]),
                "did_P1_P2": (u["P2"] - u["P1"]) - (c["P2"] - c["P1"]),
            }
        result["diff_in_diff"][ctrl] = did

    PROCESSED.mkdir(parents=True, exist_ok=True)
    write_json(PROCESSED / "metrics.json", result)
    print(f"processed: metrics.json written (n_boot={n_boot})")
