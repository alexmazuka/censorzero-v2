# Preregistration — CensorZero v2

**Study:** Did the algorithmically measurable signals that ІМІ (Інститут масової
інформації / Institute of Mass Information) publicly cited — «паркетні»
повідомлення (single-source official-only items) and «недостатній баланс»
(insufficient balance) — change across the three editorial periods of Ukrinform
implied by ІМІ's White List decisions?

**Status of this document.** Committed to git *before* the raw snapshot is
collected and before any statistic in this study is computed. The git commit
date of this file is the preregistration timestamp. Any later change to the
plan is recorded in the **Deviations** section at the bottom and never
overwrites the original text.

---

## 1. Conflict of interest — declared first

The author of this study, **Oleksiy Matsuka**, was the head of Ukrinform during
period P1 (appointed 2023-11-09; departed 2024-05-24) — the period after which
Ukrinform was excluded from ІМІ's White List. The author is therefore **not a
neutral party**: the study examines decisions that concerned his own tenure.

Mitigations, all verifiable from this repository:
- this preregistration fixes hypotheses, definitions, and the analysis plan
  before computation (git history proves ordering);
- every published number is regenerated from the committed raw snapshot by CI
  on every push and compared byte-for-byte (any drift fails the build);
- one classifier codebase is applied identically to all periods and all media,
  enforced by tests;
- the gold-standard validation sample is annotated blind to period and outlet;
- the possible outcome «no signal either way in this proxy metric» is declared
  acceptable and expected in advance (see §8).

This declaration also appears on the first screen of the published site and at
the top of the README.

## 2. Background facts (from archived primary sources)

- 2024-04-26 — ІМІ published its H1-2024 White List; Ukrinform was excluded.
  The original announcement URL now returns 404 and was never archived
  (0 Wayback captures found as of the v1 evidence collection). The
  best-preserved on-domain statement of the reason is ІМІ's own retrospective
  news item (2024-11-29): «Агенції порадили звернути більше уваги на
  дотримання стандарту балансу і переглянути кількість "паркетних" новин у
  стрічці.»
- ІМІ's clearest public description of the parket problem (Sept-2024
  standards report): «Найчастіше на Укрінформі порушувався стандарт балансу.
  Такі порушення на сайті фіксуються в паркетних матеріалах. Ці матеріали…
  часто не мають новинної цінності, замість цього акцентуючи на діяльності
  певних посадовців.»
- 2025-12-16 — ІМІ's H2-2025 White List re-included Ukrinform: «Після
  тривалої перерви до Білого списку повернувся Укрінформ, який удосконалив
  дотримання балансу і продемонстрував відповідальне ставлення до аудиторії.»
- **ІМІ publishes no numeric threshold** for parket share or balance
  compliance in any archived document. Everything measured here is therefore
  the study's own operationalization (a *proxy*), mapped as closely as the
  public record allows onto ІМІ's published wording. This study cannot and
  does not claim to replicate ІМІ's internal assessment.
- ІМІ's own published method is expert manual review of ~100 items per outlet
  drawn from two specific days, twice a year. This study instead measures the
  full article stream. The two designs answer related but not identical
  questions; this asymmetry is carried into §10 (Limitations).

## 3. Hypotheses

ІМІ's decisions imply a specific temporal pattern: the cited signals should be
*worse* during P1 (exclusion period) than before (P0), and *better* by P2
(re-inclusion period) than during P1. We test whether that pattern is present
in the proxy metrics.

- **H1 (parket, P0→P1).** The rubric-standardized parket-proxy rate of
  Ukrinform in P1 differs from P0. Decision-implied direction: P1 > P0.
- **H2 (parket, P1→P2).** Same, P2 vs P1. Decision-implied direction: P2 < P1.
- **H3 (balance, P0→P1)** and **H4 (balance, P1→P2).** Same comparisons for
  the balance-proxy rate.
- **H5 (difference-in-differences, descriptive).** The change in Ukrinform's
  standardized rates between periods differs from the contemporaneous change
  in control media. Because control coverage is partial (§6), H5 is
  preregistered as descriptive only — no causal claim will be made.

All tests are two-sided. Finding *no* significant differences, or differences
opposite to the decision-implied direction, are both admissible outcomes and
will be reported exactly as found. An absence of signal will be stated as
«within this proxy metric, no signal» — not as proof that ІМІ was wrong, and
not softened into a weaker claim.

## 4. Periods and their justification

| Key | Window (publication date, inclusive) | Rationale |
|-----|-----|-----|
| P0 | 2023-05-01 … 2023-10-31 | Six months immediately before Matsuka's appointment; Ukrinform on the White List. |
| P1 | 2023-11-09 … 2024-04-25 | Matsuka's tenure start (2023-11-09) to the day before the exclusion announcement (2024-04-26). Matches ІМІ-adjacent reporting that the exclusion followed «моніторинг його роботи в останні пів року». |
| P2 | 2025-07-01 … 2025-12-15 | The H2-2025 half-year assessed by the list that re-included Ukrinform, ending the day before the re-inclusion announcement (2025-12-16). |

Declared weaknesses of these boundaries, known before computation:
1. ІМІ's *actual* H1-2024 monitoring window is unknown (the primary document
   is lost); P1 is anchored to the announcement date and public retrospective
   wording, not to a verified assessment window.
2. Likewise the exact H2-2025 assessment window behind the re-inclusion is
   not published; P2 assumes the half-year reading.
3. The interval 2024-04-26 … 2025-06-30 (exclusion persisted, three further
   lists) is outside the scope of this study and is not audited.

Articles are assigned to periods by **publication date extracted from the
article's own JSON-LD `datePublished`** — never by sitemap `lastmod` (v1 used
lastmod; live checks found articles misdated by ≥2 days at period boundaries).

## 5. Corpus definition

**Treatment outlet:** ukrinform.ua (Ukrainian-language version).

**Rubric universe (primary analysis):** the seven news rubrics
`rubric-polytics`, `rubric-economy`, `rubric-society`, `rubric-regions`,
`rubric-ato`, `rubric-tymchasovo-okupovani`, `rubric-vidbudova`.
Sensitivity scenario S-world additionally includes `rubric-world`.

**Military-bulletin handling:** the primary analysis **excludes
`rubric-ato`** (war summaries are structurally single-source; treating them
as parket would be a category error). The with-ATO scenario is computed and
published alongside. Both denominators are fixed by this paragraph.

**URL discovery.** Ukrinform's weekly sitemaps
(`/sitemap/{year}/{week:02d}.xml`) have *expired* for 2023 (verified live:
HTTP 302→404). Discovery therefore uses, in this fixed order of precedence:
1. Wayback Machine captures of the weekly sitemap XMLs (status-200 captures
   exist; archived copies are committed to `data/raw/discovery/`);
2. the v1 study's committed URL inventories (P0, P1 incl. the Jan–Feb-2024
   recovery list, P2), committed here with provenance manifests;
3. live weekly sitemaps where still available (P2 and later).
The union of these channels defines the URL universe. Per-channel counts and
overlaps are published. The v2 corpus must be a superset of every v1
inventory for the same window; any URL present in an inventory but
unfetchable is listed with its HTTP status in a fetch-failure report — never
silently dropped.

**Immutable snapshot.** For every URL the collector stores: url,
date_published (JSON-LD), date_modified, rubric, slug, title, og_description,
full body_text, fetch timestamp, HTTP status — in sharded zstd parquet under
`data/raw/` with SHA-256 per shard. After the snapshot is committed, no
pipeline stage touches the network; the live sites are not a dependency.

## 6. Control media

Both controls are processed by **the same collector, the same parser, the
same classifier module** as Ukrinform (enforced by tests). Classification is
by article text — never by URL slug (v1's control produced 0% parket *by
construction* because its URLs carry no text; that result is retracted and
will not be cited).

- **Primary control: Українська правда (pravda.com.ua)** — news section.
  Discovery: the site's own day-archive pages for every calendar day of
  P0/P1/P2 (a census by construction, not a sample). These index pages are
  bot-protected; they are fetched once through a real browser session, the
  raw HTML committed, and article pages then fetched normally. Only
  `www.pravda.com.ua/news/…` URLs are used (no epravda / eurointegration
  cross-domain links).
- **Secondary control: Суспільне (suspilne.media)** — national news.
  The live sitemap only reaches back ~1 year (verified), so full-period
  discovery is impossible from the live site. Discovery: Wayback CDX index of
  `suspilne.media/{numeric-id}-{slug}` URLs across the three windows, plus the
  live sitemap where it overlaps. **Coverage is therefore partial and
  non-census.** Per-period discovered counts are published, Suspilne is used
  descriptively only, and every Suspilne figure carries a "partial coverage"
  label.

If a control's collected coverage for any period turns out below 50% of its
estimated publication volume for that window, that control-period cell is
reported as not usable for comparison (rule fixed here to prevent post-hoc
discretion).

## 7. Metric definitions (locked)

Definitions below are implemented in `src/censorzero/source_extraction.py`
and `src/censorzero/classification.py`, both covered by unit tests with
committed true/false example lists, and applied identically to every article
of every outlet in every period.

**Source extraction.** Attribution patterns (the v1 pattern families:
reporting verbs, «за словами / за даними», «про це повідомляє…», headline
dash-attribution, og-description attribution, «повідомили в/у…») are applied
to sentence-segmented body text. Extracted spans are normalized to canonical
entities; the **full** list of distinct entities is stored as a JSON array —
no truncation at any N. Every extracted entity is classified into exactly one
of: `ukrainian_official`, `foreign_official`, `non_official`, `unknown`.

**Entity registry.** A single versioned registry (one file,
`data/registry/entities_v2.json`) serves title, lead, and source
classification. It includes institutions *and the surnames of incumbent
first-person officials* (Зеленський, Єрмак, Шмигаль, Свириденко, Стефанчук,
Сирський, Залужний, Буданов, Умєров, Кулеба, Сибіга, Клименко, Малюк, …
full list in the file). All matching is word-boundary / morphology-aware
regex — never substring. Foreign official bodies (NATO, EU, G7, OSCE, UN,
foreign ministries and officials of other states, «МЗС РФ» etc.) carry the
`foreign_official` flag and are **excluded** from the parket definition:
parket is about domestic officialdom.

**Per-article quantities.** `sc` = count of distinct extracted entities;
`oc` = count classified `ukrainian_official`; `nc` = count classified
`non_official`; `official_focus` = a `ukrainian_official` registry entity
appears (word-boundary) in the title or the first body paragraph.

**Primary outcome — parket-proxy:**
`parket := official_focus AND sc == 1 AND oc == 1 AND nc == 0`
(exactly one attributed source, that source is a Ukrainian official, no
non-official voices, and the item is framed around an official actor).

**Secondary outcome — balance-proxy:**
`balance_risk := official_focus AND oc >= 1 AND nc == 0`
(only official voices present, regardless of their number). By construction
parket ⊂ balance_risk.

**Zero-source articles (`sc == 0`)** are *never* counted as parket (v1's
fatal flaw: 63–99.9% of its parket flags were extraction failures). They are
reported as their own published category, split into (a) military bulletins
(rubric-ato), (b) other — with the gold standard (§9) measuring how often (b)
is a parser miss vs a genuinely unattributed item.

**Sensitivity grid (published as an interactive dashboard, all cells
precomputed by the pipeline):** sc threshold ∈ {==1, ≤2}; official_focus
required ∈ {yes, no}; ATO ∈ {excluded, included}; rubric universe ∈ {7
rubrics, +world}; standardization ∈ {direct, crude}. The primary cell is the
one defined above (==1, yes, ATO excluded, 7 rubrics, direct). No cell will
be promoted to "primary" after the fact.

**Absolute levels are declared uninterpretable** — they depend on extractor
recall. Only between-period and between-outlet *contrasts* are interpreted,
and only if §9 shows recall stability across periods.

## 8. Statistical analysis plan

1. **Standardization.** Primary estimates are direct-standardized parket /
   balance rates: within-rubric period rates weighted by the pooled
   three-period rubric distribution of Ukrinform (weights published).
   Crude rates are reported as secondary.
2. **Model.** Logistic regression `parket ~ period + rubric + month`
   (month as calendar-month factor within period) on article-level data, as
   a robustness companion to standardization.
3. **Tests.** Pairwise contrasts P0–P1, P1–P2, P0–P2 for both outcomes
   (6 primary tests). P-values from two-proportion z-tests on standardized
   rates with bootstrap variance; **Holm correction across the 6 tests**;
   raw and adjusted p-values both published.
4. **Effect sizes.** Cohen's h for every contrast with 95% bootstrap CI
   (10,000 resamples, article-level, stratified by rubric, seed = 20230501).
   Interpretation bands stated in advance: |h| < 0.2 negligible; overlapping
   CI with 0 → "no detectable difference".
5. **Difference-in-differences (descriptive).** For each control with usable
   coverage: (rate_P1 − rate_P0)_Ukrinform − (rate_P1 − rate_P0)_control and
   the P1→P2 analogue, with bootstrap CIs. Labeled descriptive; no causal
   language.
6. **Decision rule for the headline conclusion.** The data are read as
   *consistent with ІМІ's implied pattern* only if BOTH: P1 standardized
   parket-proxy significantly exceeds P0 **and** significantly exceeds P2
   (Holm-adjusted p < 0.05) with |h| ≥ 0.2 in both contrasts, and the same
   qualitative pattern holds in the with-ATO scenario. Any other outcome is
   reported as «the proxy does not show the implied pattern», with all
   estimates shown. If extractor recall is found unstable across periods
   (§9), between-period conclusions are withheld entirely and the study
   reports the instability instead.

## 9. Gold-standard validation

- **Sample:** ≥ 300 Ukrinform articles, stratified proportionally to
  period × rubric cell sizes, drawn with seed 20230501 after the snapshot is
  frozen. The sample additionally always includes ІМІ's own published parket
  example («Клименко відвідав бригаду…», if present in the corpus windows).
- **Blinding:** annotators see title + body text only — no URL, date,
  rubric label, or period indicator.
- **Codebook:** `data/gold/CODEBOOK.md`, committed before annotation starts,
  operationalizing parket / non-parket per ІМІ's published wording, with
  worked examples and edge-case rules (military bulletins, foreign officials,
  multi-voice officialdom).
- **Annotators:** primary annotation of the full sample by a large language
  model (Claude, this repository's build assistant), disclosed openly;
  independent human annotation (the author) of a random ≥ 60-article
  subsample. Cohen's κ between the two published. The COI implication of
  author-annotation is acknowledged; blinding is the mitigation.
- **Published:** confusion matrix (classifier vs gold), precision, recall,
  F1 — overall AND per period; extraction-level recall (share of articles
  where the extractor found the attribution a human sees); a test of recall
  homogeneity across periods (chi-square). **Precondition rule:** if
  per-period recall differs by more than 10 percentage points or the
  homogeneity test rejects at p < 0.05, between-period trends are declared
  confounded by parsing and the study's conclusion section says exactly that.

## 10. Known limitations declared in advance

1. Proxy validity: ІМІ's assessment is expert and manual; ours is lexical
   and structural. Agreement is measured (§9), not assumed.
2. The P0/P1 discovery channel depends on archived sitemaps and v1 URL
   inventories because the live sitemaps expired; a hostile reviewer cannot
   re-run *discovery* from the live web for those windows (they can verify
   the committed archives and hashes, and re-run everything downstream).
3. Article bodies are fetched in 2026; post-publication edits are invisible
   except via `dateModified`, which is recorded and reported.
4. Control coverage is partial for Суспільне; УП day archives are complete
   but bot-gated at the index level (raw index pages committed).
5. One person holds the COI and wrote the codebook; the codebook is committed
   before annotation and the LLM annotator never sees period labels.
6. This study measures two named signals only. ІМІ's decision may have
   rested on considerations not measurable here; absence of signal in these
   proxies is not proof the decision was unfounded.

## 11. Deviations

- **2026-07-11 — Суспільне excluded from the numeric comparison.** The §6 rule
  reserved the right to drop a control whose coverage is inadequate. On
  inspection the extractor's precision on Суспільне's long-form narrative
  articles is low: its mean extracted source count is ~3× the other outlets',
  driven by false "sources" (outlet sign-offs like «Суспільне Полтава», direct-
  speech fragments, pronouns), which pushes every article to have a non-official
  voice and forces parket/balance to a degenerate 0. Because the instrument was
  not gold-validated on Суспільне (the blind gold set covers Ukrinform and УП),
  its 0% is an instrument artifact, not an editorial fact — publishing it would
  repeat v1's "control is 0 by construction" error. Суспільне is therefore
  excluded from the numeric comparison and difference-in-differences; its
  articles remain browsable on the site with an explicit notice, and the
  comparable control is Українська правда (gold-validated, n≈450). Rule made
  explicit: a control is compared only if the extractor is gold-validated on it.

- **2026-07-10 — Blind annotation scaled up as the primary between-period
  instrument.** The §9 precondition failed: the automatic proxy's recall is
  low (≈7%) and drifts across periods (0%→3%→19%, homogeneity p≈0.003), so —
  exactly as §8.6 commits — between-period conclusions from the automatic
  metric are withheld. The blind human/LLM annotation protocol of §9 (same
  codebook, same blinding) is therefore extended from a validation sample to
  a direct measurement: ~400 Ukrinform articles per period (equal allocation,
  rubric-proportional within period) and ~150 Українська правда articles per
  period as a control, drawn with fixed seeds. An independent re-annotation
  of 150 articles measures inter-annotator reliability (Cohen's κ); the
  author's blind validation of a 60-article subsample (κ vs the primary
  annotator) is part of the protocol. Impact: the primary between-period
  comparison no longer depends on extractor recall at all; its instrument is
  the committed codebook.

- **2026-07-10 — Суспільне fetched as a deterministic sample, not a census.**
  Wayback CDX discovery returned ~170k Суспільне article URLs across the three
  windows. Fetching all of them politely is infeasible and unnecessary for a
  *secondary, descriptive* control. We fetch a deterministic even-stride
  sample (URLs sorted, every ⌈N/12000⌉-th kept), targeting ~12,000 articles.
  Impact: Суспільне estimates carry wider sampling error and remain
  descriptive-only, exactly as §6 already constrained them; the primary
  Ukrinform analysis and the УП (primary control) census are unaffected. The
  full discovered URL list is committed under `data/raw/discovery/` so the
  sampling is auditable and could be expanded.
