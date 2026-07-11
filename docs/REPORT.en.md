<!-- GENERATED-FROM-FIGURES: rendered by `make readme` from docs/templates/REPORT.en.md.j2 + site/figures.json. Do not edit numbers by hand. -->

# Did Ukrinform's "parket" and balance signals change the way IMI's decisions imply? A reproducible audit

**Version:** pipeline 2.0.0 · **Full data & code:** [github.com/alexmazuka/censorzero-v2](https://github.com/alexmazuka/censorzero-v2) · **Interactive site:** [alexmazuka.github.io/censorzero-v2](https://alexmazuka.github.io/censorzero-v2/)

> **Conflict of interest.** The author, Oleksiy Matsuka, led Ukrinform during
> period P1 — the tenure after which the agency was removed from IMI's White
> List. This study is therefore built so that nothing rests on the author's
> word: hypotheses and methods were preregistered in git before computation,
> every number regenerates from a committed raw snapshot with one command, and
> CI re-checks the published figures byte-for-byte on every change.

## Abstract

When the Institute of Mass Information (ІМІ) removed Ukrinform from its White
List in April 2024, the publicly stated reasons were «паркетні» матеріали
(single-source official-record items) and insufficient balance; when it
reinstated the agency in December 2025, it credited improved balance. We
measure exactly those two signals across three editorial periods — before the
author's tenure (P0), during it (P1), and the half-year before reinstatement
(P2) — over 106 279 articles of Ukrinform and two control outlets, with
two independent instruments: an open lexical classifier and blind human-protocol
annotation of 1649 articles under a committed codebook. The automatic
classifier proved precise (precision 83%) but insensitive (recall
6%), and its recall varies by period — so, under a stop-rule fixed
in the preregistration, its between-period trend is not interpreted. The blind
measurement, which does not depend on extraction recall, finds the parket share
statistically indistinguishable across all three periods:
42.1% → 41.2% → 38.5% (homogeneity p = 0.629).
Within the signals ІМІ named publicly, the data do not show the deterioration-
then-improvement pattern its decisions imply. Smaller changes than our minimum
detectable difference (≈11 p.p.) cannot be ruled out, and ІМІ's
judgment may have rested on factors not measured here.

## 1. Background: the decisions under study

- **2024-04-26** — ІМІ publishes the H1-2024 White List without Ukrinform.
  The original announcement later disappeared from imi.org.ua (404); an
  archived copy was recovered via the Wayback Machine and is committed in this
  repository (`data/imi_evidence/`). ІМІ's retrospective wording (Nov 2024):
  «Агенції порадили звернути більше уваги на дотримання стандарту балансу і
  переглянути кількість "паркетних" новин у стрічці.»
- **2025-12-16** — the H2-2025 White List reinstates Ukrinform: «Після
  тривалої перерви до Білого списку повернувся Укрінформ, який удосконалив
  дотримання балансу…»
- ІМІ publishes **no numeric threshold** for either signal, and its own method
  is expert review of ~100 items per outlet from two days, twice a year. This
  study therefore measures ІМІ's *stated criteria*, not its internal procedure.

Periods (assignment by each article's own JSON-LD publication date):
- **P0** (2023-05-01 → 2023-10-31) — Before Matsuka's appointment — Ukrinform on the White List
- **P1** (2023-11-09 → 2024-04-25) — Matsuka's tenure — excluded from the White List
- **P2** (2025-07-01 → 2025-12-15) — After Matsuka's departure — returned to the White List

## 2. Data

106 279 in-period articles from the committed immutable snapshot:
73 316 Ukrinform (news rubrics), 31 910 Українська правда (news; the
primary control — continuously White-Listed), 1 053 Суспільне (secondary,
deterministic sample). Article bodies were captured from Web Archive snapshots
(the origin's 2023 sitemaps have expired and the live site throttles bulk
access); the archive is timestamped and stable, which strengthens
reproducibility. Discovery channels, per-URL provenance, and every fetch
failure are committed. The corpus is an ongoing seeded-random census: the
collected set is a uniform random sample of the 148k-URL universe
at any point in time.

## 3. Instruments

**Automatic proxy.** One open classifier applied identically to every article
of every outlet and period: word-boundary entity registry (incl. first-person
officials; foreign bodies flagged and excluded), attribution-pattern source
extraction, and the preregistered definition — *parket* = official framing +
exactly one source + that source a Ukrainian official + no non-official voice.

**Blind annotation.** 1649 articles labeled under the committed
codebook (`data/gold/CODEBOOK.md`) by annotators shown only title and body —
no date, period, or outlet. Inter-annotator reliability on an independent
150-article re-annotation: agreement 93%, Cohen's κ =
0.86.
## 4. Results

### 4.1 The automatic proxy disqualified itself for trend reading

Against the blind labels the classifier shows precision
83% and recall 6% — it almost never false-alarms but
misses most parket. Critically, its recall differs by period
(6/133 → 9/133 → 9/120 hits of human-labeled parket;
homogeneity p = 0.5853). The preregistration (§9) committed us, in that
event, to **withhold between-period conclusions from the automatic metric** —
we do. (Its rubric-standardized rates are published on the site for
completeness, flagged as non-interpretable.)

### 4.2 The blind measurement: no pattern in the direction ІМІ's decisions imply

Direct blind annotation, which does not depend on extraction at all
(military situation reports excluded, as preregistered):

| Period | Parket share (blind annotation) | 95% CI | n |
|---|---|---|---|
| P0 | 42.1% | [36.8%, 47.6%] | 316 |
| P1 | 41.2% | [35.9%, 46.6%] | 323 |
| P2 | 38.5% | [33.2%, 44.0%] | 312 |

Homogeneity across periods: χ² p = 0.629. Pairwise (Holm-adjusted):
- P0-P1: Δ = 0.9 p.p., Cohen's h = 0.019 [-0.137, 0.174], p(Holm) = 1.000
- P1-P2: Δ = 2.7 p.p., Cohen's h = 0.055 [-0.100, 0.211], p(Holm) = 1.000
- P0-P2: Δ = 3.6 p.p., Cohen's h = 0.074 [-0.082, 0.230], p(Holm) = 1.000

The share of single-source official-record items is statistically flat: P1 —
the period after which Ukrinform was excluded — is **not** higher than P0
(before) and **not** higher than P2 (the period credited with improvement).

Control (Українська правда, same instrument, blind): 17.8% →
15.4% → 16.3% across the same periods.

### 4.3 What this does and does not mean

**It means:** in the two signals ІМІ named publicly, measured two independent
ways over the full article stream, there is no visible deterioration in P1 and
no visible improvement by P2. The pattern implied by the exclusion-and-return
sequence does not appear in the data.

**It does not mean ІМІ acted in bad faith.** Our minimum detectable difference
is ≈11 p.p.; smaller shifts would be invisible. ІМІ's expert
assessment may weigh aspects no lexical or protocol instrument captures. The
honest formulation: *ІМІ has not shown, and we could not find.* The open
question this study poses to ІМІ is specific: **what exactly changed between
P0, P1, and P2?**

## 5. Limitations

- Proxy validity: IMI's assessment is expert and manual; ours is lexical and structural. Agreement is measured (Validation), not assumed.
- Article bodies come from Web Archive snapshots (stable, timestamped) because the site's 2023 weekly sitemaps have expired from the live web; this is if anything more reproducible, but archive coverage is incomplete — the uncovered share is published.
- Post-publication edits are invisible except via dateModified, which is recorded.
- Control Суспільне is a sample (descriptive); УП is a day-census, but its index pages are bot-gated (raw pages committed).
- One person holds the conflict of interest and wrote the codebook; the codebook is committed before annotation and the LLM annotator never sees period labels.
- Only two named signals are measured. IMI's decision may rest on factors not measurable here; absence of a signal is not proof the decision was unfounded.
- The blind annotators follow a written codebook but are LLM-based; this is
  disclosed, measured (κ above), and correctable — the packet for independent
  human re-annotation ships with the repository.

## 6. Verify everything yourself

```bash
git clone https://github.com/alexmazuka/censorzero-v2 && cd censorzero-v2
uv sync --frozen && make verify
```

`make verify` rebuilds every published number from the committed raw snapshot
and fails on any byte-level difference — the same check CI runs on every push.
Preregistration (with a dated git history and a deviations log), data
dictionary, codebook, and the archived ІМІ primary sources are all in the
repository.