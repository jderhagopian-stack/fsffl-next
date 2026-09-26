# Intrinsic Term-Structure Research Reproducibility

Date: 2026-09-26

## Frozen research branch

`research/intrinsic-term-structure-20260926`

The branch contains:
- `scripts/extract_long_horizon_player_seasons.R`;
- `scripts/run_intrinsic_term_structure_research.py`;
- `scripts/run_intrinsic_term_structure_current_shadows.py`;
- historical and current-shadow workflows;
- the read-only current production H3 snapshot metadata/value map.

## Historical model-selection run

- workflow run: `36220635330`
- head: `895df9e3f439762ebd6dbca72f447fbe1f21dab5`
- artifact ID: `10899387479`
- artifact name: `intrinsic-term-structure-research`
- digest: `sha256:ea72f312148f01b8066419e8f12cb3a04a4dbbd99fd6e0b7dc975c65cc2446b5`

Retained outputs include:
- `RESULTS.json`
- `FORECAST_HORIZON_METRICS.csv`
- `VALUE_HORIZON_METRICS.csv`
- `UNCERTAINTY_BY_HORIZON.csv`
- `SHAPLEY_BRIDGE_VALIDATION.csv`
- `HISTORICAL_CROSSOVERS.csv`
- `POSITION_DISTRIBUTIONS.csv`
- `DISCOUNT_SENSITIVITY.csv`
- `PLAYER_SEASONS.csv`

## Current post-selection run

- workflow run: `36241799792`
- head: `08e2883c639f62542887f7e164d6348580511bbd`
- artifact ID: `10905882596`
- artifact name: `intrinsic-term-structure-current-shadows`
- digest: `sha256:9f2fbb24b95b7039ac1ddd0ebe8d7fb8265b63ee4b59c92181688e1c4e596fe8`

Outputs:
- `CURRENT_HORIZON_SHADOWS.csv`
- `CURRENT_CROSSOVERS.csv`
- `CURRENT_POSITION_DISTRIBUTIONS.csv`
- `CURRENT_AGE_EFFECTS.csv`
- `CURRENT_UNCERTAINTY_INTERPRETATION.csv`
- `REPRESENTATIVE_PLAYER_CURVES.csv`
- `CURRENT_SHADOW_SUMMARY.json`

## Production reference used only for comparison

Persisted `shapley_intrinsic_contract` artifact:
- ID: **566**
- computed: **2026-09-25 03:07:50.427138+00**
- player count: **335**

The reference was not trained on, edited, replaced or republished as a new production artifact.

## No-authority-change guarantee

No production source file, Forecast coefficient, Value implementation, API route, database row, Render service or active product configuration was changed by this Research study.
