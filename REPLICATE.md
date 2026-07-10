# Replicate this study

Everything published is regenerated from the committed raw snapshot under
`data/raw/`. The live news sites are **not** a dependency of the pipeline.

## One command

```bash
git clone https://github.com/alexmazuka/censorzero-v2 && cd censorzero-v2
uv sync --frozen        # pinned env from uv.lock (+ .python-version = 3.12)
make verify             # rebuild every derived artifact and assert it is
                        # byte-for-byte identical to what is committed
```

`make verify` runs the full pipeline (`interim → processed → gold → figures →
site → readme`) and then `git diff --exit-code` over the derived artifacts. If
a single byte differs, it fails. This is exactly what CI runs on every push
(`.github/workflows/verify.yml`).

To just rebuild without the diff check: `make all`.

## Docker (hermetic)

```bash
docker build -t censorzero-v2 .
docker run --rm censorzero-v2 make all
```

The image pins `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` and installs
from `uv.lock`. Note: exact byte-for-byte reproduction of the bootstrap
confidence intervals is guaranteed on the **same CPU architecture** that
generated the committed artifacts (arm64 / Apple-silicon; CI uses a `macos-14`
runner for this reason). Rates and bootstrap p-values use only IEEE-754
`+ − × ÷` in a fixed order and are portable across platforms; Cohen's h uses
`arcsin`, whose sub-ULP cross-platform drift is why the canonical run is pinned
to one architecture. All published values are rounded to 6 decimals.

## Determinism guarantees

- Python pinned in `.python-version`; dependencies pinned in `uv.lock`.
- No wall-clock in artifacts: the "generation date" is the git commit date of
  `data/raw` (see `src/censorzero/manifest.py`).
- All randomness goes through `rng(seed)` with a preregistered seed
  (`GLOBAL_SEED = 20230501`); bootstrap resampling uses NumPy PCG64.
- JSON is canonical: sorted keys, 6-decimal floats, `NaN/Inf → null`,
  trailing newline.
- Dictionary/rubric iteration is sorted on every data path.

## Re-running collection (optional, not needed to reproduce numbers)

The snapshot is committed, so you never need to fetch. To rebuild it from
scratch (hours; polite crawl + Web Archive):

```bash
python scripts/01_snapshot.py discover-ukrinform   # weekly sitemaps (live + Wayback)
python scripts/01_snapshot.py discover-suspilne    # Wayback CDX
# pravda day-archive index pages are bot-gated: collect once via a browser
# session into data/raw/discovery/pravda_day_archives/ (see 01_snapshot.py header)
python scripts/01_snapshot.py universe             # merge channels -> url_universe.csv.gz
python scripts/01_snapshot.py fetch ukrinform --via wayback
python scripts/01_snapshot.py fetch pravda  --via origin
python scripts/01_snapshot.py fetch suspilne --via wayback
python scripts/01_snapshot.py shard                # -> data/raw/articles/*.parquet + hashes
```

## Gold standard

```bash
python scripts/gold_sample.py     # draw the blinded stratified sample (seeded)
# annotate data/gold/sample.jsonl per data/gold/CODEBOOK.md -> data/gold/annotations.csv
make gold                          # -> data/gold/report.json (PR/F1, recall drift)
```
