"""Analysis configuration — one source of truth for rubrics and scenarios.

Consumed by every stage. Period definitions live in periods.py; metric
definitions live in features.py. This module only fixes the analysis universe
and the sensitivity grid declared in PREREGISTRATION.md sections 5 and 7.
"""

# Ukrinform news rubrics used in the primary analysis.
PRIMARY_RUBRICS = (
    "rubric-polytics",
    "rubric-economy",
    "rubric-society",
    "rubric-regions",
    "rubric-ato",
    "rubric-tymchasovo-okupovani",
    "rubric-vidbudova",
)

# Additional rubric included only in the S-world sensitivity scenario.
WORLD_RUBRIC = "rubric-world"

# The war-summary rubric excluded from the primary analysis.
ATO_RUBRIC = "rubric-ato"

OUTLET_UKRINFORM = "ukrinform"
CONTROL_OUTLETS = ("pravda", "suspilne")

# Sensitivity grid axes (PREREGISTRATION §7). The primary cell is the first
# option of each axis.
SENSITIVITY = {
    "sc_threshold": [1, 2],          # parket if 1 <= sc <= threshold
    "require_focus": [True, False],  # require official_focus in title/lead
    "ato": ["excluded", "included"],
    "rubric_universe": ["primary7", "plus_world"],
    "standardization": ["direct", "crude"],
}
