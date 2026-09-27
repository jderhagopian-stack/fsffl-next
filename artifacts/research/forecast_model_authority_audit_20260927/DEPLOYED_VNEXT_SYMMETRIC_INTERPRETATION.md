# Exact Deployed vNext — Symmetric Forecast Authority Interpretation

Date: 2026-09-27  
Authority: **Research only / no production Forecast, H3 or Intrinsic change**

## Completeness correction satisfied

The audit now contains the exact deployed `forecast-vnext-a2-burr-20260922` package as its own candidate, rather than using A2, D0 or D1 ancestor evidence as a proxy.

The recovered immutable archive was verified at its recorded SHA-256 and all 40 manifest entries passed exact hash verification. Its git bundle preserves the implementation commit/tag even though the historical research branch is no longer live on GitHub.

Exact common-row join to the already-audited D1/N1/N2 production coordinate:
- total: **10,894 / 10,894 rows**;
- H2: **5,726** rows, origins 2014-2023;
- H3: **5,168** rows, origins 2014-2022;
- target-points mismatch: **0**.

The deployed candidate is evaluated with:
- frozen A2 state probabilities;
- frozen Stage-D state means;
- Burr XII M1 within-state uncertainty for QB;
- direct-Gamma M1 within-state uncertainty for RB/WR/TE.

## State / persistence layer

The deployed package's state probabilities reproduce the D1/A2 probability surface to numerical tolerance. Maximum absolute probability difference over the common replay is about **1.4e-5**.

Thus the deployed-vNext versus D1 scientific distinction on this coordinate is primarily:
1. Stage-D conditional magnitude; and
2. explicit within-state Burr/Gamma uncertainty.

It is not a materially different survival/state-probability model.

## Proper distributional score

This is the clearest positive result for the deployed package.

### H2
- deployed vNext CRPS: **20.8383**
- D1: 21.9314
- N1: 21.8650
- N2: 22.4861

Dependence-aware pairwise gain for deployed vNext:
- vs D1: **+1.0931**, 95% CI **[+0.8975,+1.3183]**
- vs N1: **+1.0268**, **[+0.6166,+1.4748]**
- vs N2: **+1.6478**, **[+1.2392,+2.0697]**

### H3
- deployed vNext CRPS: **19.1512**
- D1: 19.8195
- N1: 20.1527
- N2: 20.4100

Pairwise gain:
- vs D1: **+0.6682**, **[+0.4585,+0.8902]**
- vs N1: **+1.0015**, **[+0.4706,+1.5523]**
- vs N2: **+1.2587**, **[+0.7558,+1.8479]**

Therefore the exact deployed Burr/Gamma distribution has **supported better aggregate proper distributional quality** than every audited D1/N1/N2 alternative on both common horizons.

The improvement is not confined to QB. Against D1, deployed vNext CRPS is supported better in all eight position×horizon cells.

## Central expected-points tradeoff

The distributional gain does **not** imply central-point dominance.

### H2
MAE:
- deployed: **32.3009**
- D1: 32.1407
- N1: 32.0059
- N2: **31.7948**

Deployed vs D1 and N1 is uncertain. N2's aggregate H2 MAE advantage over deployed is narrowly supported.

### H3
MAE:
- deployed: **31.2630**
- D1: 30.9129
- N1: **30.2538**
- N2: 30.5335

Deployed is supported worse on aggregate MAE than D1, N1 and N2.

Positionally, the tradeoff is real:
- H2 QB: deployed has the best central MAE, but differences are uncertain; its CRPS advantage is supported.
- H2 WR: N2 has a supported MAE advantage over deployed, while deployed has supported better CRPS.
- H2 TE: D1 has a very small supported MAE advantage, while deployed has supported better CRPS.
- H3 RB: N1 has a supported MAE advantage; deployed-vs-N1 CRPS is uncertain in the RB cell even though deployed beats D1/N2 on CRPS.
- H3 WR: N2 has a supported MAE advantage; deployed-vs-N2 CRPS is uncertain, while deployed beats D1/N1 on CRPS.
- H3 TE: D1 has a supported MAE advantage; deployed has supported better CRPS.

This is a **point-vs-distribution tradeoff**, not evidence for automatic deployed-model authority.

## Bias

The exact Stage-D deployed central expectation is positively biased on the replay:
- H2 bias: **+4.27 points**
- H3 bias: **+4.35 points**

D1 is closer to zero on aggregate central bias. That limitation remains part of authority evidence even though deployed vNext has the better CRPS.

## Calibration and tail evidence

The deployed package retains exact q10/q50/q90/q99 rows, but D1/N1/N2 common-row artifacts do not retain comparable quantiles. A direct four-model quantile-calibration comparison is therefore **uncomparable** and is not invented.

The deployed empirical q90/q99 coverage is close to nominal overall, but lower quantile coverage is heavily affected by the atom at zero/out state and should not be read as ordinary continuous-quantile calibration.

More importantly, the original dense QB tail gate remains binding evidence:
- 1.45x historical maximum: **FAIL**
- 1.50x: **FAIL**
- 1.55x: **FAIL**

The symmetric audit does not erase those failures because the package is deployed.

## Horizon×position authority consequence

The existing map must be read with deployed vNext added to the P-coordinate best-supported set.

There is still **no universal Y2/Y3 family winner**:
- deployed vNext owns the strongest aggregate proper distribution score;
- D1 remains a strong state/distribution anchor with better central bias/MAE in some cells;
- N1 retains supported central point advantage in H3 RB;
- N2 retains supported central point advantage in H2/H3 WR;
- several QB/TE cells remain metric tradeoffs.

The scientifically correct status is a **cell- and metric-specific authority set**, not incumbent authority and not blanket replacement.

## Y1 boundary

This comparison is only the future-model Y2/Y3 coordinate.

Current Year-1 Forecast remains governed provider/source evidence and is not made scientifically authoritative by the vNext model-family result.

## Downstream consequence

Stage 4 may now proceed with exactly four frozen candidates:
- deployed VNEXT_A2_BURR;
- D1;
- N1;
- N2.

Within-state Burr/Gamma uncertainty must be preserved as Forecast uncertainty. The existing Intrinsic central expectation consumes state probabilities/state means and therefore must not be silently changed merely because vNext carries a richer tail distribution.

**Audit completeness correction: satisfied.**
