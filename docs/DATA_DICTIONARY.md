# Data dictionary

Every artifact the pipeline reads or writes, with every column. Paths are
repo-relative. Stages: `interim → processed → gold → figures → site → readme`
(`make all`), all pure functions over `data/raw/`.

## `data/raw/articles/{outlet}_{month}.parquet` — immutable snapshot (INPUT)

One row per successfully fetched article. Produced by
`scripts/01_snapshot.py shard`; SHA-256 of each shard in
`data/raw/articles/SHA256SUMS.json`. The pipeline reads only these.

| column | type | meaning |
|--------|------|---------|
| `url` | str | canonical article URL (identity key) |
| `outlet` | str | `ukrinform` \| `pravda` \| `suspilne` |
| `date_published` | str | ISO-8601 publication datetime from the page's JSON-LD (never sitemap lastmod) |
| `date_modified` | str | ISO-8601 last-modified from JSON-LD, if any |
| `rubric` | str | Ukrinform: `rubric-*`; controls: `news` |
| `slug` | str | URL slug with the leading numeric id stripped |
| `title` | str | article headline |
| `og_description` | str | `og:description` meta |
| `body_text` | str | full article body (block-level text, joined by newlines) |
| `parse_error` | str/null | non-null if title/body were missing (such rows are excluded at shard time) |
| `parser_version` | str | `snapshot/parsers.py::PARSER_VERSION` |
| `fetch_status` | int | HTTP status of the fetch (200 for committed rows) |
| `final_url` | str | URL after redirects (Wayback snapshot URL when `source=wayback`) |
| `source` | str | `wayback` (Web Archive snapshot) \| `origin` (live site) |
| `discovery_channels` | str | `\|`-joined channels that surfaced the URL (`sitemap`, `v1_p0`, `v1_corpus`, `v1_recovered`, `wayback_cdx`, `day_archive`) |
| `sitemap_lastmod` | str | lastmod from the sitemap, if discovered via one (diagnostic only) |

## `data/raw/fetch_failures.csv` — fetch-failure report (INPUT/provenance)

Every URL that was in scope but not committed as an article. Columns:
`outlet`, `url`, `fetch_status`, `parse_error`, `discovery_channels`.
Nothing is dropped silently — a URL is either an article row or a row here.

## `data/raw/discovery/url_universe.csv.gz` — fetch input (provenance)

The union of all discovery channels. Columns: `outlet`, `url`, `channels`,
`sitemap_lastmod`. Consumed by `01_snapshot.py fetch`, not by the pipeline.
Bulk discovery bytes (sitemap XML, CDX pages, day-archive HTML) are gitignored
and regenerable via `01_snapshot.py discover-*`.

## `data/interim/articles.parquet` — per-article features (DERIVED)

Produced by the `interim` stage. One row per in-period article (rows whose
`date_published` falls outside all periods are dropped and counted).

| column | type | meaning |
|--------|------|---------|
| `outlet`, `period` | str | outlet; period key `P0`\|`P1`\|`P2` (by publication date) |
| `url`, `date_published`, `date_modified`, `rubric`, `slug`, `title` | | as in the snapshot |
| `sc` | int | count of distinct extracted sources |
| `oc` | int | of those, classified `ukrainian_official` |
| `fc` | int | classified `foreign_official` |
| `nc` | int | classified `non_official` |
| `uc` | int | classified `unknown` |
| `official_focus` | bool | a Ukrainian-official entity appears in title or lead |
| `parket` | bool | `official_focus ∧ sc==1 ∧ oc==1 ∧ nc==0` (primary outcome) |
| `balance_risk` | bool | `official_focus ∧ oc≥1 ∧ nc==0` (secondary outcome) |
| `is_ato` | bool | `rubric == rubric-ato` (military bulletins) |
| `sources_json` | str | full `span::label` list of extracted sources (no truncation) |
| `classifier_version`, `extraction_version`, `parser_version` | str | versions |

## `data/interim/counts.json` — coverage (DERIVED)

`raw_rows`, `dropped_out_of_period`, and `by_outlet_period[outlet][period]`.

## `data/processed/metrics.json` — statistics (DERIVED)

Keys: `n_boot`; `standard_weights` (rubric → pooled count); `rates`
(`parket`/`balance` → period → `{n, n_flagged, crude, standardized}`);
`contrasts` (`outcome:Pa-Pb` → `{rate_a, rate_b, diff, cohen_h, h_ci_low,
h_ci_high, p_raw, p_holm}`); `logistic` (`outcome` → period odds ratios +
Wald p, CI); `sensitivity` (grid-cell key → outcome → period → `{n, rate}`);
`diff_in_diff` (control → `{status, parket, balance, did_P0_P1, did_P1_P2}`);
`control_coverage` (control → period → n). Sensitivity key format:
`sc{1,2}_focus{0,1}_ato{excluded,included}_{primary7,plus_world}_{direct,crude}`.

## `data/gold/` — metric validation

- `CODEBOOK.md` — annotation rules (committed before annotation).
- `sample.jsonl` — blinded sample: `{id, title, body}` only.
- `sample_key.csv` — `id, url, period, rubric` (not shown to annotator).
- `annotations.csv` — ground truth: `id, label(parket|non_parket),
  military_bulletin, uncertain, note`.
- `report.json` (DERIVED, `gold` stage) — `overall`/`by_period`
  `{tp,fp,fn,tn,precision,recall,f1,n}`, `sc0_breakdown`, `recall_drift`
  `{per_period, chi2, p_value, recall_spread_pp, confounded}`.

## `site/figures.json` — single source of truth for site + README (DERIVED)

`pipeline_version`, `periods`, `coverage`, `standard_weights`, `rates`,
`contrasts`, `logistic`, `sensitivity`, `diff_in_diff`, `control_coverage`,
`gold_standard` (=gold report or null), `limitations` (uk/en), `verification`
(`reproduce_command`, `inputs_sha256`), `verdict` (preregistered decision
rule), `conflict_of_interest`, `notes`. No number appears in HTML/README
except through this file.

## `site/explorer/` — chunked explorer (DERIVED)

`index.json` (`shards[]` with per-shard counts, `totals` per outlet) plus one
`{outlet}_{period}_{month}.json` per shard (display columns only). Chunked so
the browser never loads a monolithic file.

## `data/manifests/lineage.json` — provenance (DERIVED)

`pipeline_version`; `raw_snapshot` (`commit`, `committed_at` of the last commit
touching `data/raw`); `inputs_sha256` (every raw shard); `outputs_sha256`
(every derived artifact). Ties published numbers to exact input bytes.
