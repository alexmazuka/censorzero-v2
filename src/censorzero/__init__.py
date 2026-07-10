"""CensorZero v2 — reproducible audit of IMI parket/balance signals.

Every published number is derived from the committed raw snapshot by
`python -m censorzero.pipeline` (or `make all`). The live websites are not
a dependency of any pipeline stage.
"""

# Bumped manually on any change that can affect published numbers.
# Recorded in every output manifest.
PIPELINE_VERSION = "2.0.0"
