# Model Versioning and Reproducibility

FSFFL NEXT must be able to explain which model produced an answer and reproduce that answer from pinned inputs.

## Versioned elements

Material versions include:

- canonical schema/normalization version;
- forecast model version;
- valuation model version;
- simulation model version;
- team-utility model version;
- trade/behavior model version;
- parameter/evidence bundle version;
- reporting/API schema version when output contracts change.

## Production and challenger status

A model implementation may be:

- `RESEARCH` — exploratory, not relied on for decisions;
- `CHALLENGER` — eligible for structured comparison;
- `PRODUCTION` — current authoritative implementation for its defined responsibility;
- `RETIRED` — preserved for historical reproducibility but no longer authoritative.

Only one implementation should be authoritative for a specific conceptual responsibility and production context at a time.

## Promotion rule

A challenger is not promoted because it is newer, cleaner, or agrees with legacy FSFFL.

Promotion requires evidence appropriate to the responsibility, potentially including:

- historical/out-of-sample accuracy;
- calibration;
- stability and sensitivity testing;
- sanity cases;
- economic/football coherence;
- computational reliability;
- uncertainty behavior;
- regression testing against known failure modes.

Different results from legacy FSFFL are acceptable when better justified.

## Reproducible run record

Material runs should eventually record:

- input state identity;
- model component versions;
- parameter/evidence bundle versions;
- provider snapshot identifiers;
- timestamp;
- configuration;
- stochastic seed/run count where applicable;
- output schema version.

## Breaking changes

Breaking semantic changes require explicit version increments and migration notes. Renaming a value while changing its meaning is prohibited without a contract change.

## No hidden latest

Historical analysis must not silently use the current production parameter or model version when the requested experiment requires a pinned version. `latest` may be a convenience for live execution, not a substitute for reproducibility.
