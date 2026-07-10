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

# Verify that regenerating all derived artifacts changes nothing (bit-for-bit).
# CI runs this against a clean checkout; any diff fails the build.
verify: all
	git diff --exit-code -- data/interim data/processed data/manifests site/figures.json README.md
	git status --porcelain data/interim data/processed data/manifests site/figures.json | (! grep .)

# Remove derived artifacts (never touches data/raw or data/gold).
clean-derived:
	rm -rf data/interim/* data/processed/* site/figures.json
