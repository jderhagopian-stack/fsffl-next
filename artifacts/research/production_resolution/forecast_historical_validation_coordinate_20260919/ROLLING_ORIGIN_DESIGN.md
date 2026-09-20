# FSFFL NEXT - Primary rolling-origin / walk-forward validation design

## Scope and horizon mapping

The governed redevelopment uses project horizon code h=2 for Y2 and h=3 for Y3. A source season T therefore evaluates against target season T+h in the durable historical rows. The Phase-2 panel ends in 2025.

Primary evaluation origins are frozen at:
- Y2: source seasons 2014-2023 (10 genuinely forward origins; 5,726 eligible rows across all positions).
- Y3: source seasons 2014-2022 (9 genuinely forward origins; 5,168 eligible rows across all positions).

The first origin remains 2014 because that is the pre-existing governed selection start, not a newly chosen favorable start year.

## At each origin T

1. Reconstruct source state, source/state percentile, age/experience, prior-history coverage, role/opportunity, and any already-governed inputs using only source-T and earlier data exactly as in the durable redevelopment code.
2. Refit the frozen control/candidate methodology using only rows whose realized target is fully resolved by T-1.
3. For Y2/h2, follow the existing fit rule: historical rows must satisfy source_season < T and source_season+horizon <= T-1. The shared state layer may use its governed h1/h2 pooling only under the same resolved-target rule.
4. For Y3/h3, train only h3 rows with source_season < T and source_season+3 <= T-1.
5. Evaluate the frozen candidate specification on source season T exactly once. No origin may change features, candidate family, thresholds, regularization, or scoring rules.
6. Report origin-level CRPS, valid discrete probability scores, calibration/coverage, tail diagnostics, conditional-active bias, and raw-point MAE.

## Temporal robustness

Primary authority uses all eligible origins, not a single two-year window. Report:
- share of origins with positive proper-score gain;
- median origin-level gain;
- worst-origin regression;
- leave-one-origin-out pooled gain;
- two-way player/source-year clustered uncertainty;
- moving-block source-year bootstrap sensitivity with block length equal to the forecast horizon;
- subgroup calibration with explicit row counts.

No every-year-win requirement is imposed, but a candidate whose pooled result is driven by one origin cannot be called robust.

## Exceptional developmental-RB tail

The exceptional tail remains a predeclared structural diagnostic, not a six-row binary gate. For a Y3 developmental-RB candidate, primary authority comes from the full supported cell plus continuous magnitude-conditioned evidence. p90+/p95+ summaries are co-primary only when the candidate claims to repair that tail, and must include leave-one-year-out and leave-one-player-out influence diagnostics.

## Fresh confirmation

No fully observed pristine Y3 confirmation source later than 2022 exists in the governed panel. Source 2023 Y3 targets 2026 and is not complete in the panel. It can be prospectively frozen now for later confirmation after the 2026 season is complete, but it is not current evidence.

Y2 source 2023 -> target 2025 is fully observed and has not been used for developmental-RB candidate-specific evaluation, but it cannot substitute for a fresh Y3 confirmation of the unresolved Y3 problem.