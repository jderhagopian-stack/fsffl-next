# League-agnostic future scoring promotion - migration note

Date: 2026-09-19  
PR: #147  
Validated code head: `68c4905b41817239c60a45b4c65b94fb2745c887`

## What changed

The private-beta Intrinsic/Shapley runtime no longer uses the position-average future-scoring bridge as its authoritative Years 2/3 scoring conversion.

The validated player-specific translation is now the PR runtime implementation:

```
two frozen preseason sources (FFToday + Razzball)
  -> governed frozen equal-weight raw-stat baseline
  -> direct league-specific Year 1 scoring
  -> frozen P0 standard/non-PPR trajectory
  -> player-specific Year1 league/standard ratio
  -> league-specific Years 2/3 point representation
  -> Intrinsic/Shapley
```

The implementation is in `src/fsffl/product/i1_player_scoring.py`. The former candidate import path remains only as a compatibility shim so the completed architecture-gate evidence remains reproducible.

## What did not change

- P0/I1 fitted artifacts, routes, probabilities, persistence, state definitions, and parameters are unchanged.
- Standard/non-PPR remains a frozen P0 compatibility coordinate only.
- Year 1 remains direct scoring from the preserved frozen preseason raw-stat baseline under the connected league's rules.
- Active probability is not re-applied.
- Scoring conversion is not re-applied.
- No market, owner, roster, or ranking input enters the translation.
- Scoring-rule coverage is not broadened.

## Fail-closed behavior

The authoritative runtime now refuses to fall back to the old position bridge when player-specific evidence, exact two-source preseason lineage, identity mapping, or supported scoring semantics are unavailable.

## Superseded runtime

`LeagueScoringNormalizedI1Predictor` and the position-average multipliers remain in the repository for historical evidence/tests and are not deleted, but `PrivateBetaShapleyContractLoader` no longer uses them as the authoritative future-scoring path.

## TE premium boundary

The player-specific translation mechanism is compatible with a TE-premium coordinate once the governed Year-1 scoring engine can directly materialize that scoring rule. The current scoring engine intentionally classifies `bonus_rec_te` as unsupported, so the promoted runtime fails closed rather than silently approximating or expanding coverage.

## Stop boundary

This is implementation promotion inside PR #147 only. No merge, deployment, or production release is authorized by this note.
