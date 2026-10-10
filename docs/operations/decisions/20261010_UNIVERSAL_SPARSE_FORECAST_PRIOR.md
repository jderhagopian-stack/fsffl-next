# Universal sparse-player Forecast prior — Management decision

Date: 2026-10-10  
Authority: Management approval in the current implementation session; universal Forecast requirement in [Management Continuity](../MANAGEMENT_CONTINUITY.md).

## Decision

Approve a new, internal, historical empirical prior for a canonical QB/RB/WR/TE player when an approved ordinary projection is absent. The prior is based on fully observed historical outcomes in the same scoring coordinate and is conditioned on position, age band, and experience band. It uses the most recent 15 completed seasons and backs off to position-only evidence when a narrower group is too small. The initial minimum is 100 historical outcomes, giving at least ten observations in each nominal 10% tail before producing p10/p90 estimates.

The model is fitted/materialized once for a shared evaluation-season/evidence version. Player lookups do not fit a model. Candidate identity is canonical and dynamic; the 335 reference set is not an allowlist. The forecast carries empirical uncertainty, training cutoff, sample count, evidence tier, and source/model version. A player-specific authority failure is returned when there is insufficient point-in-time history or a required identity/position/scoring authority is absent.

Uncertainty intervals require a second, temporally later calibration set of rolling-origin predictions. Use split-conformal interval scores from the most recent 10 completed calibration seasons, conditioned by position and evidence tier when sample support permits and otherwise pooled by position. Calibrate the central 50% interval with its 50% finite-sample score quantile and the central 80% interval with its 90% score quantile, widening intervals as required; preserve the empirical median and report out-of-time coverage. Repeated player-seasons make simple independent-row confidence intervals approximate. A prior without a compatible calibration record is not emitted as a ready Forecast.

## Safeguards

- Training labels must come from fully observed player-season outcomes with an explicit standard/non-PPR scoring coordinate. A genuinely observed zero may be retained; missing seasons are never silently changed to zero.
- For evaluation season `S` and timestamp `as_of`, training and calibration targets must be earlier than `S`, and their recorded observation availability must be no later than `as_of`.
- Apply the unchanged league scoring authority after the prior is estimated. The prior cannot consume Market values, research-only provider projections, later observations, arbitrary constants or player names as identity.
- Do not alter P0 coefficients/routes, Career formulas, the 335 reference output, #370 completeness, publication/State fences, or #445 bounded job admission.
- This decision approves the fallback model family and its validation method. It does not certify an unvalidated calibration artifact or authorize deployment/merge.

## First implementation tranche

Implement the point-in-time empirical prior and rolling conformal interval-calibration boundary, validate it against the preserved accepted historical panel, and expose it through the canonical Forecast observation contract. Follow with the dynamic P0 candidate-evidence adapter and Career materialization so the same prior can flow through P0 and Career under exact scoring and State authority.

The frozen 335 and exact-State 25 remain regression populations only. The broad waiver cohort and unusual-candidate on-demand path remain later #405 tranches.
