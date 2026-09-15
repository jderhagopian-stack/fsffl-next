# FSFFL NEXT - Shapley Precision + Historical Target Decomposition Protocol

Research-only. Frozen before any new >128-permutation league-scale result is inspected.

## Frozen economic candidate

Do not change the PR #139 deployment game, coalition semantics, Shapley attribution, 0.85 discount, three-horizon Forecast integration, scoring, eligibility, career-state inputs, low-end behavior, or holding=0 governance.

## Track P - precision protocol

League-scale cases: the same strict PIT full-supply season/horizon pools used by PR #139 across all 12 scored holdout seasons and horizons Y1/Y2/Y3. No named-player selection.

Permutation ladder: 128, 256, 512, 1024. A 2048-permutation run is predeclared now as a research reference only. Each case uses one fixed seed and common random permutations; every lower budget is a prefix of the 2048 sequence.

Minimum denominator for relative metrics: 5.0 annual Shapley fantasy-point units. Values below 5.0 remain in absolute-error and rank diagnostics but are excluded from relative-SE/change denominators.

At each budget report p50/p90/p95 absolute Monte Carlo SE, p50/p90/p95 relative SE, successive-budget relative change, efficiency residual, runtime, peak memory, and scaling. Rank diagnostics compare each budget with the predeclared 2048 reference within reference-defined nonzero value cohorts: bottom 20%, middle 60%, top 20%. Report cohort Spearman rank correlation and adjacent close-pair ordering agreement, where close pairs have reference values >=5 and relative gap <=10%.

### Practical precision pass standard

Shapley is computationally practical at 1024 permutations only if ALL hold:

1. aggregate p95 relative SE <= 10% for values >=5;
2. aggregate p95 absolute SE <= 2.0 annual Shapley fantasy-point units;
3. aggregate p95 relative change from 512 to 1024 <= 10% for values >=5;
4. median case-level Spearman rank correlation versus 2048 reference >=0.995 in top, middle, and low nonzero cohorts, with no cohort median below 0.990;
5. close-pair ordering agreement >=90%;
6. maximum absolute efficiency residual <=1e-8 of full-game value (numerical identity check);
7. observed 1024-budget runtime for the full Track P ladder is <=30 minutes on the GitHub research runner and peak RSS <=7 GiB.

Rationale: Intrinsic is intended as a cardinal coordinate, so 20% relative instability is too loose as a production-quality target. A 10% p95 relative standard plus a 2-point absolute cap permits small Monte Carlo noise without allowing that noise to dominate meaningful player-level differences. Rank criteria ensure seemingly acceptable cardinal errors are not masking unstable ordering. The 2048 run is not a post-result rescue budget; it is frozen here as the independent convergence reference.

Track P decision rules:
- P1 if 1024 meets all practical criteria, or if 2048 meets them and its measured cost still meets the same <=30 minute / <=7 GiB practical limit.
- P2 if a fixed budget can meet the statistical criteria but measured/extrapolated cost violates practical limits.
- P3 if 2048 still fails the statistical criteria.

## Track T - decomposition protocol

Use the same 6,758 strict PIT holdout rows as PR #139. Do not fit or rescale Shapley.

Coordinates:
- Forecast Shapley: frozen PR #139 result.
- Realized Shapley H3: realized actual fantasy production for seasons t,t+1,t+2, each season attributed by the same frozen league-wide assignment game/Shapley rule, discounted 1, 0.85, 0.85^2.
- Realized Shapley H6: closest target-horizon match using realized seasons t..t+5 and the same Shapley rule, discounted by 0.85^offset.
- Established target: frozen six-season smoothed marginal-lineup target from the D2 harness.
- Primitive A and exact hard-marginal controls: frozen controls from PR #139.

Use 2048 fixed-seed permutations for realized season-level Shapley attribution so Track T is interpreted against the predeclared high-budget research reference, not the rejected 128 approximation. Where a player's future season is absent/nonpositive, contribution is zero, matching the established target's realized-evidence handling.

Decomposition metrics: MAE, mean bias, median bias, Pearson correlation, Spearman correlation, descriptive OLS intercept/slope only (never adopted), decile calibration, position and age/subgroup summaries, and row-level component differences:
- Forecast component = Forecast Shapley - Realized Shapley H3;
- Horizon component = Realized Shapley H3 - Realized Shapley H6;
- attribution/object component = Realized Shapley H6 - Established target.

Primary low-end cohorts use the established target's existing frozen definitions for elite/fringe/developmental/young/prime/aging to avoid post-result regrouping. Full-supply Y1 bottom-quintile share remains a separate system-share diagnostic and must not be conflated with holdout fringe rows.

No Broad Market, League Market, transactions, owners, actual-roster Simulation, named-player sentiment, or holding economics may enter either track.
