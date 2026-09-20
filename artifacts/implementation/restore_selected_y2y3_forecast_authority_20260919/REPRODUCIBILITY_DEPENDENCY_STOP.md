# FSFFL NEXT - Restore Selected Y2/Y3 Forecast Authority

Date: 2026-09-19  
Final classification: **STOP - REPRODUCIBILITY DEPENDENCY**

## Executive result

The required runtime repair cannot be completed exactly from the durable selected artifacts without making a new modeling choice.

The directive requires the authoritative future stack to preserve, in order:

1. state routing: QB = A2+C+D; RB/WR/TE = A2+D;
2. selected D0/D1 conditional-production routing;
3. the separately frozen M1a continuous within-state magnitude carry-forward;
4. the frozen two-prior-season consistency adjustment;
5. the already-validated player-specific league-scoring translation;
6. calendar -> Intrinsic/Shapley.

The exact durable D0/D1 deployment package was recovered and hash-verified, but it is not a serialization of that full ordered stack.

## What was recovered exactly

Exact redeveloped final fitted package:
- Library id: `libfile_aaa8c63f86e08191a89f092f02367472`
- SHA-256: `ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7`
- bytes: 107,778
- historical replay: 20,610 rows
- max probability difference: 4.996e-16
- max point difference: 1.421e-13
- route mismatches: 0

Exact corrected preseason source coordinate:
- 335 players
- SHA-256: `eda43a5e297ffe46550af5c3fbf98a1d32545fc15925a9e49c6620427043307a`

The old selected-candidate diagnostic also durably records:
- frozen candidate = routed Forecast + M1a + exact two-prior consistency;
- Y2 M1a coefficient = 0.07939942531895901;
- Y3 M1a coefficient = 0.07812314495946265.

## Why the durable D0/D1 package is not enough

The recovered D0/D1 package directly predicts conditional production from serialized production models. Its D1 design contains prior-two mean/gap/coverage features inside that fitted model.

The directive, however, separately requires M1a and then the frozen two-prior adjustment after D0/D1. No durable deployment artifact was found that serializes that exact ordered combination.

The older selected-candidate evidence preserves M1a/consistency coefficient summaries, but not a deployment-grade, row-complete package that unambiguously combines those layers with the later recovered D0/D1 producer for all 335 players.

Therefore either of the apparent implementation shortcuts would be invalid:
- wiring the D0/D1 package alone would silently omit the directive-required separate M1a layer;
- adding M1a on top by reconstruction would create a new, unvalidated combination across model generations.

That is precisely the directive's reproducibility stop condition.

## Implementation trial and cleanup

A bounded implementation trial was used only to test whether the recovered D0/D1 package could be embedded and replayed exactly. During reconciliation, the semantic mismatch above was identified before final promotion.

The final stop commit restores the PR runtime tree to the task-start state and retains only this evidence. No partial replacement of Y2/Y3 authority is left active at the final head.

## Final sanity gate

Not run.

The directive says the final 335-player Y1/Y2/Y3 sanity gate may begin only after architecture wiring passes. Architecture wiring cannot pass while the exact M1a/D0-D1 combination is unresolved, so no final board or named-player credibility judgment is fabricated.

## Exact missing dependency

A durable, deployment-grade artifact or executable specification that unambiguously defines the selected **D0/D1 -> M1a -> frozen two-prior** future-production stack at the 2026 preseason standard coordinate, including the exact point at which M1a is applied and the complete frozen parameterization needed to reproduce all 335 players without fitting.

If management supplies or recovers that artifact, implementation can resume from this boundary. It must not be inferred from named-player outputs or assembled by judgment.

## Governance

- PR #147 remains open and unmerged.
- Protected main is unchanged.
- Research authority is unchanged.
- No merge or deployment.
- No refit, retraining, retuning, reselection, approximation, or scoring-coverage expansion.

**STOP - REPRODUCIBILITY DEPENDENCY.**
