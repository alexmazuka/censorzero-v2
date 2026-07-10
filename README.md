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
and **insufficient balance**. We measure exactly those signals, with one
classifier, across three periods:

- **P0** (2023-05-01 → 2023-10-31) — Before Matsuka's appointment — Ukrinform on the White List
- **P1** (2023-11-09 → 2024-04-25) — Matsuka's tenure — excluded from the White List
- **P2** (2025-07-01 → 2025-12-15) — After Matsuka's departure — returned to the White List

IMI publishes no numeric threshold for these signals; our metric is a declared
**proxy** (see [PREREGISTRATION.md](PREREGISTRATION.md)). Absolute levels are
uninterpretable and are not interpreted — only between-period contrasts are,
and only conditional on parser-recall stability.

## Headline result (standardized parket rate, ATO excluded, primary 7 rubrics)

| Period | Standardized parket | Standardized balance-risk | N articles |
|--------|--------------------:|--------------------------:|-----------:|
| P0 | 4.81% | 9.46% | 2363 |
| P1 | 4.16% | 8.73% | 2447 |
| P2 | 6.64% | 12.13% | 2852 |

**Preregistered decision rule:** the data are read as consistent with IMI's
implied pattern only if P1 parket significantly exceeds *both* P0 and P2
(Holm-adjusted p < 0.05, |Cohen's h| ≥ 0.2).

**Verdict from this run:** implied pattern supported =
**False**
(P1 > P0: False;
P1 > P2: False).

### Primary contrasts (Cohen's h, 95% bootstrap CI, Holm-adjusted p)

| Contrast | rate A | rate B | Cohen's h [95% CI] | p (raw) | p (Holm) |
|----------|-------:|-------:|:------------------:|--------:|---------:|
| balance:P0-P1 | 9.46% | 8.73% | 0.025 [-0.033, 0.081] | 0.3858 | 0.5876 |
| balance:P0-P2 | 9.46% | 12.13% | -0.086 [-0.144, -0.032] | 0.0026 | 0.0104 |
| balance:P1-P2 | 8.73% | 12.13% | -0.112 [-0.166, -0.058] | 0.0002 | 0.0010 |
| parket:P0-P1 | 4.81% | 4.16% | 0.031 [-0.027, 0.089] | 0.2938 | 0.5876 |
| parket:P0-P2 | 4.81% | 6.64% | -0.079 [-0.134, -0.025] | 0.0038 | 0.0114 |
| parket:P1-P2 | 4.16% | 6.64% | -0.110 [-0.165, -0.057] | 0.0000 | 0.0000 |

## Reproduce it (one command)

```bash
git clone https://github.com/alexmazuka/censorzero-v2 && cd censorzero-v2
uv sync --frozen && make verify
```

`make verify` rebuilds every derived artifact from the committed raw snapshot
and fails if a single byte differs from what is committed. CI runs the same
check on every push. See [REPLICATE.md](REPLICATE.md) for the Docker path and
[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) for every column of every
artifact.

## How to read it honestly

- **Fact** (what the code computes): the standardized rates and contrasts above.
- **Interpretation** (what it may mean): stated only where the decision rule
  and gold-standard preconditions are met.
- **Hypothesis** (not established): anything about intent or causation. With
  one partial control we make no causal claim.

Full method, hypotheses, and declared limitations:
[PREREGISTRATION.md](PREREGISTRATION.md) (committed before any computation).
Parser precision/recall and the gold standard:
published in figures.json / the site.