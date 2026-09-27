# Integrated B0 / B1 / I1 / I2 — Symmetric Authority Reinterpretation

Date: 2026-09-27  
Source: exact original OOS artifact `10422858437` from head `c12402df1b7fa0bfbb3d994bdcf791d80e103a0c`.

## Recovery limitation

The exact OOS artifact is still available and contains 7,512 rows / 6,263 factually resolved rows across 2014-2022, H1/H2.

It did **not** persist player IDs or the full state-probability × state-mean vectors. Therefore:
- exact same-row metric comparisons are available;
- paired row-bootstrap intervals are persisted only as sensitivity checks;
- player-cluster uncertainty is **not recoverable** and is not invented;
- CRPS is unavailable and not imputed;
- these candidates are not falsely joined by row order to later D0/D1/N1/N2 evidence.

## Controls versus integrated models

B0/B1 use the same scalar point means; B1 materially improves several state/persistence dimensions over B0.

I1 and I2 both materially improve the integrated factual-state representation and expected points versus B0/B1:
- overall MAE: B0/B1 **42.827**, I1 **39.713**, I2 **39.064**;
- overall state Brier: B0 0.13118, B1 0.13077, I1 **0.12162**, I2 **0.12184**;
- overall Spearman: B0/B1 0.516, I1 0.621, I2 **0.633**.

Thus B0/B1 remain useful historical controls, but are not the best-supported whole representations on their own factual-state coordinate.

## I1 versus I2

### H1
- I1 MAE 38.010; I2 **37.475**.
- Exact same-row point sensitivity favors I2 by 0.535.
- State/persistence Brier differences are extremely small and their row-sensitivity intervals cross zero.
- I2 has lower state log loss centrally.

QB is the clearest point difference:
- H1 QB: I1 75.115 vs I2 **71.243** MAE.

RB / WR / TE are effectively tied on the available uncertainty evidence.

### H2
- I1 MAE 41.714; I2 **40.930**.
- Same-row point sensitivity favors I2 by 0.784.
- State/persistence Brier differences remain small.
- H2 QB again carries the largest point difference: I1 81.492 vs I2 **77.139**; I2 also has lower state Brier on the paired-row sensitivity check.
- RB / WR / TE remain close.

## Symmetric disposition

The historical label `selected=I1` is retained as provenance but has **no audit authority**.

The symmetric re-read is:
- **I1 and I2 are broadly tied on factual-state probability quality**;
- **I2 has the stronger expected-points / rank evidence, driven especially by QB**;
- because player-cluster uncertainty and CRPS cannot be recovered from the old artifact, this audit does not convert that point advantage into blanket I2 whole-Forecast authority.

These H1/H2 factual-state results also remain a different target coordinate from the later production-row D0/D1/N1/N2 studies. Cross-coordinate numerical MAE values must not be compared directly.

Production Forecast / H3 / Intrinsic remain unchanged.
