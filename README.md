<!-- GENERATED FILE — do not edit by hand.
     Rendered by `make readme` from docs/templates/README.md.j2 + site/figures.json.
     Every number below comes from figures.json; edit the template or the data, never this file. -->

# CensorZero v2 — reproducible audit of IMI parket/balance signals in Ukrinform

[![verify](https://github.com/alexmazuka/censorzero-v2/actions/workflows/verify.yml/badge.svg)](https://github.com/alexmazuka/censorzero-v2/actions/workflows/verify.yml)

> **Conflict of interest.** The author of this study led Ukrinform during period P1. See PREREGISTRATION.md section 1. Reproducibility, not the author's word, is the evidence: every number here is regenerated from the committed raw snapshot and checked bit-for-bit in CI.

## What this is

An open, end-to-end reproducible measurement of the two signals IMI (Institute
of Mass Information) publicly named when it excluded — and later re-included —
Ukrinform on its White List: **«паркет»** (single-source, official-only items)
and **insufficient balance**. Two independent instruments over 125 539
articles across three periods:

- **P0** (2023-05-01 → 2023-10-31) — Before Matsuka's appointment — Ukrinform on the White List
- **P1** (2023-11-09 → 2024-04-25) — Matsuka's tenure — excluded from the White List
- **P2** (2025-07-01 → 2025-12-15) — After Matsuka's departure — returned to the White List

IMI publishes no numeric threshold for these signals; our metrics are declared
**proxies** (see [PREREGISTRATION.md](PREREGISTRATION.md)).

## Primary result — blind annotation (1649 articles, κ = 0.86)

The primary between-period instrument is blind human-protocol annotation under
a committed codebook (annotators see only title and body — no date, period, or
outlet). It does not depend on the automatic extractor at all.

| Period | Parket share (blind annotation) | 95% CI | n |
|--------|--------------------------------:|:------:|--:|
| P0 | 42.1% | [36.8%, 47.6%] | 316 |
| P1 | 41.2% | [35.9%, 46.6%] | 323 |
| P2 | 38.5% | [33.2%, 44.0%] | 312 |

Homogeneity across periods: p = 0.629; minimum detectable
difference ≈ 11 p.p. Control (Українська правда, same blind
instrument): 17.8% → 15.4% → 16.3%.

**The deterioration-then-improvement pattern implied by IMI's decisions does
not appear in the data.** Inter-annotator reliability on an independent
150-article re-annotation: agreement 93%, Cohen's κ =
0.86.

## The automatic metric disqualified itself — and we say so

Against the blind labels the open classifier shows precision 83%
but recall 6%, and its recall differs across periods
(homogeneity p = 0.5853). Under the stop-rule fixed in the
preregistration (§9), **its between-period trend is therefore not
interpreted**. Its rubric-standardized rates and the preregistered contrast
machinery remain published in `site/figures.json` for completeness, flagged
non-interpretable; absolute levels were declared uninterpretable from the
start.

## Reproduce it (one command)

```bash
git clone https://github.com/alexmazuka/censorzero-v2 && cd censorzero-v2
uv sync --frozen && make verify
```

`make verify` rebuilds every derived artifact from the committed raw snapshot
and fails if a single byte differs from what is committed. CI runs the same
check on every push. See [REPLICATE.md](REPLICATE.md) for the Docker path,
[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) for every column of every
artifact, and the full report: [English](docs/REPORT.en.md) /
[Українською](docs/REPORT.uk.md).

## How to read it honestly

- **Fact** (what the code computes): the blind-measurement table above and
  everything in `site/figures.json`.
- **Interpretation** (what it may mean): stated only where the preregistered
  decision rules and validation preconditions are met.
- **Hypothesis** (not established): anything about intent or causation. We
  make no causal claim, and absence of a signal is not proof IMI's decision
  was unfounded — it is an open question to IMI: what exactly changed?

Full method, hypotheses, deviations log, and declared limitations:
[PREREGISTRATION.md](PREREGISTRATION.md) (committed before any computation).