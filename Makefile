# CensorZero v2 — single entrypoint pipeline.
# `make all` reproduces every published artifact from the committed raw snapshot.
# The live websites are NOT a dependency of this pipeline.

UV ?= uv
RUN = $(UV) run --frozen

.PHONY: all env interim processed gold figures site readme test verify clean-derived

all: interim processed gold figures site readme

env:
	$(UV) sync --frozen

interim:
	$(RUN) python -m censorzero.pipeline interim

processed:
	$(RUN) python -m censorzero.pipeline processed

gold:
	$(RUN) python -m censorzero.pipeline gold

figures:
	$(RUN) python -m censorzero.pipeline figures

site:
	$(RUN) python -m censorzero.pipeline site

readme:
	$(RUN) python -m censorzero.pipeline readme

test:
	$(RUN) pytest -q

# Verify that regenerating the PUBLISHED artifacts changes nothing (bit-for-bit).
# Scope = figures.json (single source of truth) + README + integer counts +
# lineage hashes. data/processed/metrics.json is intentionally excluded: it
# carries the logistic-regression companion whose iterative MLE is not
# bit-stable across platforms (rates + bootstrap p-values, which ARE stable,
# live in figures.json and are gated here). CI runs this on a clean checkout.
VERIFY_PATHS = site/figures.json README.md data/interim/counts.json data/manifests/lineage.json \
  docs/REPORT.uk.md docs/REPORT.en.md site/report_uk.html site/report_en.html \
  site/explorer

verify: all
	git diff --exit-code -- $(VERIFY_PATHS)
	git status --porcelain -- $(VERIFY_PATHS) | (! grep .)

# Remove derived artifacts (never touches data/raw or data/gold).
clean-derived:
	rm -rf data/interim/* data/processed/* site/figures.json
