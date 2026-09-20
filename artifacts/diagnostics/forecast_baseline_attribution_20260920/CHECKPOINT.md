# Forecast Baseline Attribution Diagnostic - Durable Checkpoint

Date: 2026-09-20

## Recovered starting state

- PR #147: open/unmerged.
- Implementation branch: `implementation/forecast-intrinsic-i1-shapley`.
- Recovered PR head before diagnostic: `34470dce369df2c9d5454ebbd481317c5ab76d12`.
- Protected main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- Diagnostic work was forked to `research/forecast-baseline-attribution-diagnostic-20260920` from the exact PR head above.

## Persisted diagnostic artifacts

- `MANAGEMENT_REPORT.md` - commit `9cd17ab4bb3f7072d0baa3c2f1e6460ee8334abb`
- `ROUTE_INFLUENCE_MATRIX.csv` - commit `8ff2393588ab771489fe7b607f7cf26e929f03bd`
- `CONTINUOUS_EVIDENCE_RESPONSE_CURVES.csv` - commit `14e528462eaaf06367eac5a53e84f3f4cd2ef86c`
- `EQUATION_AND_FEATURE_LINEAGE.md` - commit `ecb2f6cdd4699b86d79b5e14ada360c6a0159e01`
- `DIAGNOSTIC_EVIDENCE.json` - commit `6605139eed7bba1a025d31bf662ffe6cccd2d02c`

## Final classification

**B. LOCALIZED RB BASELINE / SHRINKAGE PROBLEM**

The mathematical pooling mechanism is shared across Forecast, but the empirical evidence that it becomes materially problematic is localized to developmental RB Y3. State probabilities are strongly individualized; conditional production is substantially pooled around shared position/state anchors. Developmental-RB Y3 high-source compression originates primarily inside conditional production, with state mix secondary and disappearance smaller. Current P0 uncertainty contains only the discrete state mixture and does not emit a within-state productive-survivor distribution.

## Decision boundary

PR #147 remains on management hold. No implementation fix was authorized or attempted. The minimum next research question and a single bounded preregistration boundary are recorded in the management report and diagnostic evidence.

## Hard stop

No changes were made to PR #147, main, production route authority, P0 coefficients, fitted distributions, Simulation, Value, Intrinsic, or Shapley. No model was fit, refit, tuned, merged, or deployed.

This checkpoint commit is the durable stopping point; its own SHA must be verified externally after commit creation.
