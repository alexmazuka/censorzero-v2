"""Single pipeline entrypoint: `python -m censorzero.pipeline [stage]`.

Stages (run in order by `make all`):
  interim    raw parquet -> per-article extraction + classification
  processed  interim -> aggregated metrics, statistics
  figures    processed -> site/figures.json + data/manifests/lineage.json
  site       processed -> explorer data chunks for the static site
  readme     figures -> README.md rendered from template

Each stage reads only committed inputs and writes deterministic outputs.
No stage touches the network.
"""

import sys

STAGES = ("interim", "processed", "gold", "figures", "site", "readme")


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in (*STAGES, "all"):
        print(f"usage: python -m censorzero.pipeline [{'|'.join((*STAGES, 'all'))}]")
        return 2
    wanted = STAGES if argv[0] == "all" else (argv[0],)
    for stage in wanted:
        run_stage(stage)
    return 0


def run_stage(stage: str) -> None:
    # Stage implementations land with the corresponding milestone; until the
    # raw snapshot is committed the pipeline fails loudly on purpose so that
    # CI stays red rather than green-by-vacuity.
    if stage == "interim":
        from .stages import interim

        interim.run()
    elif stage == "processed":
        from .stages import processed

        processed.run()
    elif stage == "gold":
        from .stages import gold

        gold.run()
    elif stage == "figures":
        from .stages import figures

        figures.run()
    elif stage == "site":
        from .stages import site

        site.run()
    elif stage == "readme":
        from .stages import readme

        readme.run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
