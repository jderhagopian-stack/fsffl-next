# FSFFL NEXT - Developmental RB distribution-shape research conclusion

## Classification
B. DISTRIBUTIONAL DIRECTION SUPPORTED, BUT NO CANDIDATE EARNS AUTHORITY

## Plain-language conclusion
Yes, FSFFL can represent an exceptional young RB as having both survivor upside and downside without pretending to know the path in advance. The preregistered empirical within-state distributions do exactly that while leaving D1 state probabilities and expected points unchanged.

That direction improves Y3 proper scoring honestly: in frozen 2014-2020, S1 improves full-cell CRPS by 0.811 points with 95% interval [0.519, 1.109], and S2 improves it by 0.806 [0.511, 1.097]. Both also improve pooled four-region Brier score while reproducing D1 expected points to floating-point tolerance.

But neither candidate calibrates the exceptional p95+ tails well enough. D1 already under-allocates productive-survivor mass there. S1/S2 spread the within-state distribution, but in the frozen p95+ sample they move even more probability from survivor into the middle region; the preregistered combined survivor/downside calibration gate therefore fails.

The single locked 2021-2022 replication preserves the positive CRPS direction (S1 +0.513; S2 +0.505), but it does not repair p95+ tail calibration and four-region Brier uncertainty spans zero. The holdout does not rescue either candidate.

## Architecture
The candidate form is compatible with Forecast -> Simulation -> Value: Forecast would emit state probabilities plus within-state production distributions; Simulation would sample the state and production realization once; Value would consume the governed expectation/distribution without adding a second collapse haircut. This contract remains research-only because no candidate earned authority.

## Stop
P0/D1 remains the frozen production control for Y3 developmental RB. PR #147 stays on hold. No production implementation, merge, or deploy is authorized. A different uncertainty family would require a new management directive; this stage may not redesign from the locked holdout.