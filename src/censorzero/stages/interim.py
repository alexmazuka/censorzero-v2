"""interim stage: raw article snapshot -> per-article features + period.

Pure function over data/raw/articles/*.parquet. Writes:
  data/interim/articles.parquet  (one row per in-period article, deterministic)
  data/interim/counts.json       (coverage counts, no wall-clock)
"""

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from ..canonical import write_json
from ..features import compute_features
from ..periods import period_of

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_ARTICLES = REPO_ROOT / "data" / "raw" / "articles"
INTERIM = REPO_ROOT / "data" / "interim"

INTERIM_COLUMNS = [
    "outlet", "period", "url", "date_published", "date_modified", "rubric",
    "slug", "title", "sc", "oc", "fc", "nc", "uc", "official_focus",
    "parket", "balance_risk", "is_ato", "sources_json",
    "classifier_version", "extraction_version", "parser_version",
]


def _s(v) -> str:
    """Coerce a possibly-NaN/None parquet cell to a plain string.
    pandas yields float NaN for null text, and `NaN or ""` is NaN (NaN is
    truthy) — which then breaks string ops downstream."""
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(v)


def _to_date(iso) -> date | None:
    if not iso or not isinstance(iso, str):
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(iso[:10])
        except ValueError:
            return None


def run() -> None:
    shards = sorted(RAW_ARTICLES.glob("*.parquet"))
    if not shards:
        raise SystemExit(
            "data/raw/articles/ is empty — run scripts/01_snapshot.py first. "
            "The pipeline does not fetch; it only reads the committed snapshot."
        )
    raw = pd.concat((pd.read_parquet(s) for s in shards), ignore_index=True)

    rows = []
    coverage = {"raw_rows": int(len(raw)), "by_outlet_period": {}, "dropped_out_of_period": 0}
    for rec in raw.itertuples(index=False):
        d = _to_date(getattr(rec, "date_published", None))
        period = period_of(d) if d else None
        if period is None:
            coverage["dropped_out_of_period"] += 1
            continue
        feat = compute_features(
            _s(getattr(rec, "title", "")),
            _s(getattr(rec, "body_text", "")),
            _s(getattr(rec, "og_description", "")),
        )
        rubric = getattr(rec, "rubric", None)
        rubric = _s(rubric) or None
        rows.append({
            "outlet": rec.outlet,
            "period": period,
            "url": rec.url,
            "date_published": d.isoformat(),
            "date_modified": getattr(rec, "date_modified", None),
            "rubric": rubric,
            "slug": getattr(rec, "slug", None),
            "title": getattr(rec, "title", None),
            "sc": feat.sc, "oc": feat.oc, "fc": feat.fc, "nc": feat.nc, "uc": feat.uc,
            "official_focus": feat.official_focus,
            "parket": feat.parket,
            "balance_risk": feat.balance_risk,
            "is_ato": rubric == "rubric-ato",
            "sources_json": feat.sources_json,
            "classifier_version": feat.classifier_version,
            "extraction_version": feat.extraction_version,
            "parser_version": getattr(rec, "parser_version", None),
        })

    df = pd.DataFrame(rows, columns=INTERIM_COLUMNS)
    df = df.sort_values(["outlet", "period", "url"]).reset_index(drop=True)

    for (outlet, period), part in df.groupby(["outlet", "period"], sort=True):
        coverage["by_outlet_period"].setdefault(outlet, {})[period] = int(len(part))

    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_parquet(INTERIM / "articles.parquet", engine="pyarrow",
                  compression="zstd", index=False)
    write_json(INTERIM / "counts.json", coverage)
    print(f"interim: {len(df)} in-period articles "
          f"({coverage['dropped_out_of_period']} dropped out-of-period)")
