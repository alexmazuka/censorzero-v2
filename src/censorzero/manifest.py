"""Lineage manifests.

Design note (why not `git rev-parse HEAD`): derived artifacts are committed
together with the code that produced them, so a manifest cannot contain the
hash of its own commit. Instead the manifest pins the *inputs*: the last
commit that touched data/raw (the immutable snapshot) plus SHA-256 of every
raw shard. Both are stable once the snapshot is committed, which makes the
manifest — and therefore the whole pipeline output — bit-for-bit reproducible
at any later commit. CI checks exactly that.
"""

import subprocess
from pathlib import Path

from . import PIPELINE_VERSION
from .canonical import sha256_file, write_json

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
MANIFEST_DIR = REPO_ROOT / "data" / "manifests"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def raw_snapshot_ref() -> dict:
    """Commit hash and date of the last commit touching data/raw.

    This is the pipeline's notion of "generation date": the date the input
    snapshot was fixed in git — never the wall clock.
    """
    commit = _git("log", "-1", "--format=%H", "--", "data/raw")
    cdate = _git("log", "-1", "--format=%cI", "--", "data/raw")
    if not commit:
        raise SystemExit(
            "data/raw has no git history yet — commit the raw snapshot first. "
            "The pipeline refuses to run on uncommitted inputs."
        )
    return {"commit": commit, "committed_at": cdate}


def raw_shard_hashes() -> dict[str, str]:
    shards = sorted(RAW_DIR.rglob("*.parquet"))
    if not shards:
        raise SystemExit("data/raw contains no parquet shards — nothing to process.")
    return {str(p.relative_to(REPO_ROOT)): sha256_file(p) for p in shards}


def write_lineage(outputs: dict[str, str]) -> None:
    """Write data/manifests/lineage.json.

    `outputs` maps repo-relative output path -> SHA-256 of that file.
    """
    lineage = {
        "pipeline_version": PIPELINE_VERSION,
        "raw_snapshot": raw_snapshot_ref(),
        "inputs_sha256": raw_shard_hashes(),
        "outputs_sha256": dict(sorted(outputs.items())),
    }
    write_json(MANIFEST_DIR / "lineage.json", lineage)
