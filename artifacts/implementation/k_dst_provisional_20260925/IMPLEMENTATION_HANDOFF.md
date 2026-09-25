# FSFFL NEXT — 2026 Provisional K/DST Implementation Handoff

Updated: 2026-09-25

## State
**ACTIVE — PR #237 ACCEPTANCE**

Management authority:
- `docs/operations/workstreams/RESEARCH.md` — “2026 provisional K/DST degraded-authority mode”
- PR #233 / merge `79c1f0c0aa094e4b1e3f6aa41eacd08c6bf1d6e8` — governed 2026 late-start ROS foundation

Implementation PR:
- **#237 — Forecast: add provisional 2026 K/DST partial-rule authority**

## Implemented contract
The provisional tier is structurally distinct from canonical `ForecastObservation`. It cannot be inserted into the existing canonical Forecast runtime artifact and therefore cannot silently become Value/Simulation/Decision/Search truth.

The contract:
- is hard-bound to season 2026 and ROS horizon;
- consumes only accepted, rights-cleared provider rows;
- preserves the existing independent-source minimum by independence group;
- scores only supported raw coordinates or exact algebraic transforms;
- carries included coordinates, omitted coordinates, source ids, independence groups and content-hash provenance;
- preserves the explicit unavailable 2026 preseason-comparison status;
- never claims full-rule authority or simulation-grade uncertainty.

## K treatment
For the Management-authorized Hodor 50+/60+ case:
- governed `FG_MADE_50_PLUS` supplies only the common five-point base across 50+ makes;
- governed `FG_MADE_60_PLUS` may supply only the incremental +1;
- absent qualifying 60+ evidence, that +1 coordinate is explicitly omitted;
- no 60+ frequency allocation or 50+/60+ split is estimated.

Existing exact transforms remain usable, including same-horizon attempt-minus-make misses and equal-coefficient 0–29 combination. Full PR #233 scoring/coverage behavior remains unchanged.

## D/ST treatment
Only qualifying linear projected coordinates contribute to the provisional total.

Nonlinear PA/YA bucket rules are omitted without transformation from aggregate PA/YA. Rare events that do not satisfy the independent-source gate are likewise omitted.

## Uncertainty
The accepted 2024 reduced-fingerprint measurements are retained as explicit empirical references:
- K season relative RMSE: `0.38418847933549305`
- K weekly CV: `0.5223274618193781`
- D/ST season relative RMSE: `0.21402833115231343`
- D/ST weekly CV: `0.6381941339011228`

They are **not** applied as provisional-total variance. Omitted-coordinate uncertainty is machine-readable as `unquantified_not_imputed`, and the contract remains `simulation_grade=False`.

## Downstream authority
Allowed only with provisional metadata attached:
- Presentation
- readiness
- analytics/API exposure of the provisional contract itself

Explicitly blocked:
- Value
- Simulation
- Team Utility
- Decision
- Search/Optimization

If the existing full-authority assessment becomes green, the provisional builder refuses to supersede it and directs callers to the full Forecast path.

## Persistence and Presentation
Provisional forecasts use their own durable artifact kind:
`late_start_provisional_k_dst_forecast`

They do not use:
- canonical Forecast runtime artifact identity;
- annual preseason artifact identity;
- the raw late-start snapshot artifact identity.

Presentation serializes the explicit label `Provisional 2026 ROS K/DST`, authority tier, included/omitted coordinates, uncertainty limits, provenance, readiness, and full-authority blockers.

## Acceptance tests
Focused coverage includes:
- K 50+ five-point base with omitted 60+ increment;
- governed 60+ incremental contribution without frequency reallocation;
- research-only rights failure;
- shared-independence-group anti-double-counting;
- D/ST linear scoring with PA buckets and undercovered rare events omitted;
- exact attempt-minus-make transform;
- downstream model-consumer denial;
- persistence/presentation separation;
- hard non-2026 rejection;
- automatic full-authority supersession.

Repository-wide configured acceptance workflows must be green on the final reconciled PR head before merge.

## Non-goals / unchanged gates
This implementation does not:
- create provider rights;
- manufacture a second exact-capability source;
- promote Hodor-total uncertainty;
- create a 2026 preseason comparison;
- change 2027+ authority;
- weaken the full K/DST gate;
- feed provisional K/DST totals into canonical Value/Simulation/Decision/Search.

## Next state
After PR acceptance/merge, canonical operations state must record that the bounded provisional implementation is complete. Actual private-beta provisional rows can exist only when qualifying rights-cleared current ROS evidence is available; research-only CBS evidence remains non-promoting.
