"""Statistics unit tests — known values and invariants."""

import math

import numpy as np

from censorzero import stats


def test_cohen_h_known():
    # equal proportions -> 0
    assert stats.cohen_h(0.5, 0.5) == 0.0
    # symmetric sign
    assert stats.cohen_h(0.2, 0.1) == -stats.cohen_h(0.1, 0.2)
    # textbook: h for 0.5 vs 0.6
    assert math.isclose(stats.cohen_h(0.6, 0.5), 0.20135792, rel_tol=1e-6)


def test_standardization_removes_mix_shift():
    # Same within-rubric rates in both groups but different mixes -> equal
    # standardized rates (Simpson guard).
    a = {"x": np.array([1, 0, 0, 0]), "y": np.array([1, 1, 0, 0] * 25)}
    b = {"x": np.array([1, 0, 0, 0] * 25), "y": np.array([1, 1, 0, 0])}
    w = {"x": 1.0, "y": 1.0}
    ra = stats.direct_standardized_rate(a, w)
    rb = stats.direct_standardized_rate(b, w)
    assert math.isclose(ra, rb, abs_tol=1e-9)
    assert math.isclose(ra, (0.25 + 0.5) / 2)


def test_contrast_and_holm_deterministic():
    rng_a = {"r": np.array([1] * 30 + [0] * 70)}
    rng_b = {"r": np.array([1] * 10 + [0] * 90)}
    w = {"r": 1.0}
    c1 = stats.contrast("A", rng_a, rng_b, w, seed_offset=1, n_boot=500)
    c1b = stats.contrast("A", rng_a, rng_b, w, seed_offset=1, n_boot=500)
    # deterministic given seed
    assert c1.h == c1b.h and c1.p_raw == c1b.p_raw
    assert c1.rate_a == 0.30 and c1.rate_b == 0.10
    assert c1.h_ci_low < c1.h < c1.h_ci_high


def test_holm_monotone_and_scaled():
    class R:
        def __init__(self, p):
            self.p_raw = p
            self.p_holm = float("nan")

    rs = [R(0.01), R(0.02), R(0.04)]
    stats.holm(rs)
    # smallest * m, then non-decreasing
    assert math.isclose(rs[0].p_holm, 0.03)
    assert rs[0].p_holm <= rs[1].p_holm <= rs[2].p_holm
    assert all(r.p_holm <= 1.0 for r in rs)
