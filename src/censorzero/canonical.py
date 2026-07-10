"""Determinism utilities.

Rules enforced project-wide:
- No `date.today()` / wall-clock time in any artifact: dates come from git
  (see manifest.py).
- No unordered iteration on the data path: every dict serialized with
  sort_keys, every list explicitly sorted by a stated key.
- All floats in published artifacts are rounded to FLOAT_DECIMALS before
  serialization so that byte-for-byte comparison is meaningful.
- Randomness only through `rng(seed)` with a preregistered seed.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

FLOAT_DECIMALS = 6

# Preregistered seed for every stochastic step (bootstrap, sampling).
GLOBAL_SEED = 20230501  # P0 start date, chosen before any computation


def rng(offset: int = 0) -> np.random.Generator:
    """Deterministic generator. `offset` separates independent uses."""
    return np.random.Generator(np.random.PCG64(GLOBAL_SEED + offset))


def _round_floats(obj: Any) -> Any:
    # NaN/Infinity are not valid JSON — browsers' JSON.parse rejects them. Map
    # non-finite floats to null so every emitted artifact is strict JSON.
    if isinstance(obj, (float, np.floating)):
        x = float(obj)
        return round(x, FLOAT_DECIMALS) if math.isfinite(x) else None
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, fixed float precision, UTF-8, newline EOF.

    allow_nan=False guarantees strict JSON (NaN/Inf already mapped to null)."""
    return json.dumps(_round_floats(obj), ensure_ascii=False, sort_keys=True,
                      indent=1, allow_nan=False) + "\n"


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(obj), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
