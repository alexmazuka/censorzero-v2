"""Statistics for the study — pure, deterministic, unit-tested.

Implements PREREGISTRATION.md section 8:
- direct standardization by rubric,
- Cohen's h with bootstrap 95% CI (fixed seed, stratified resampling),
- two-proportion contrast p-values from the bootstrap distribution,
- Holm correction across the preregistered family of tests.
"""

import math
from dataclasses import dataclass

import numpy as np

from .canonical import rng

BOOTSTRAP_N = 10000


def cohen_h(p1: float, p2: float) -> float:
    """Cohen's h effect size for two proportions."""
    phi1 = 2 * math.asin(math.sqrt(max(0.0, min(1.0, p1))))
    phi2 = 2 * math.asin(math.sqrt(max(0.0, min(1.0, p2))))
    return phi1 - phi2


def direct_standardized_rate(
    flags_by_rubric: dict[str, np.ndarray], weights: dict[str, float]
) -> float:
    """Weighted mean of within-rubric rates.

    flags_by_rubric: rubric -> 0/1 array of the outcome for that rubric in the
    period. weights: rubric -> standard weight (need not be normalized; they
    are renormalized over rubrics present with data)."""
    num = 0.0
    wsum = 0.0
    # Sorted rubric order fixes the sequence of +,*,/ so the result is
    # bit-identical across platforms (IEEE-754 correctly-rounded ops; no
    # transcendentals here). This is what makes the bootstrap p-values, which
    # depend on rate differences, cross-platform reproducible.
    for rubric in sorted(flags_by_rubric):
        flags = flags_by_rubric[rubric]
        if len(flags) == 0:
            continue
        w = weights.get(rubric, 0.0)
        if w == 0.0:
            continue
        num += w * float(flags.mean())
        wsum += w
    return num / wsum if wsum > 0 else float("nan")


def crude_rate(flags: np.ndarray) -> float:
    return float(flags.mean()) if len(flags) else float("nan")


@dataclass
class ContrastResult:
    label: str
    rate_a: float
    rate_b: float
    diff: float
    h: float
    h_ci_low: float
    h_ci_high: float
    p_raw: float
    p_holm: float = float("nan")


def _resample_stratified(
    flags_by_rubric: dict[str, np.ndarray], generator: np.random.Generator
) -> dict[str, np.ndarray]:
    # Sorted order so the PCG64 draw sequence is tied to a fixed rubric order,
    # making every resample reproducible regardless of dict insertion order.
    out = {}
    for rubric in sorted(flags_by_rubric):
        flags = flags_by_rubric[rubric]
        n = len(flags)
        out[rubric] = flags if n == 0 else flags[generator.integers(0, n, size=n)]
    return out


def contrast(
    label: str,
    a_by_rubric: dict[str, np.ndarray],
    b_by_rubric: dict[str, np.ndarray],
    weights: dict[str, float],
    seed_offset: int,
    n_boot: int = BOOTSTRAP_N,
) -> ContrastResult:
    """Standardized-rate contrast A vs B with bootstrap CI for Cohen's h and a
    two-sided bootstrap p-value for the rate difference.

    The p-value is the bootstrap achieved significance level: 2 * min(share of
    resampled diffs <= 0, share >= 0), i.e. how often the resampled difference
    fails to keep the observed sign."""
    rate_a = direct_standardized_rate(a_by_rubric, weights)
    rate_b = direct_standardized_rate(b_by_rubric, weights)
    diff = rate_a - rate_b
    h = cohen_h(rate_a, rate_b)

    g = rng(seed_offset)
    hs = np.empty(n_boot)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        ra = direct_standardized_rate(_resample_stratified(a_by_rubric, g), weights)
        rb = direct_standardized_rate(_resample_stratified(b_by_rubric, g), weights)
        hs[i] = cohen_h(ra, rb)
        diffs[i] = ra - rb

    h_lo, h_hi = np.percentile(hs, [2.5, 97.5])
    share_le = float(np.mean(diffs <= 0))
    share_ge = float(np.mean(diffs >= 0))
    p_raw = min(1.0, 2 * min(share_le, share_ge))
    return ContrastResult(label, rate_a, rate_b, diff, h, float(h_lo), float(h_hi), p_raw)


def holm(results: list[ContrastResult]) -> list[ContrastResult]:
    """Holm step-down correction over a family of contrasts (in place)."""
    order = sorted(range(len(results)), key=lambda i: results[i].p_raw)
    m = len(results)
    running_max = 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, (m - rank) * results[i].p_raw)
        running_max = max(running_max, adj)  # enforce monotonicity
        results[i].p_holm = running_max
    return results
