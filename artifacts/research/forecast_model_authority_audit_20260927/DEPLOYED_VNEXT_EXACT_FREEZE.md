# Exact Deployed vNext Forecast Audit Freeze

Date: 2026-09-27  
Status: **FROZEN BEFORE DEPLOYED-PACKAGE AUTHORITY SCORING**  
Authority: Research only; no production change.

## Required audit subject

The symmetric Forecast Model Authority Audit now treats the exact deployed future-model package as a separately identified whole-Forecast candidate:

- candidate ID: `VNEXT_A2_BURR`;
- production model version: `forecast-vnext-a2-burr-20260922`;
- deployed source: `fsffl:forecast_vnext_a2_burr_frozen`;
- research implementation commit: `122e802f327baf2fc7989ab635a68dfdc481d63f`;
- immutable tag: `research-freeze/a2-burr-20260922`;
- tag object: `b12c23008b2879af29f3f94c683de18ccbcaf264`;
- archive: `FSFFL_NEXT_A2_Burr_Implementation_Handoff_20260922.tar.gz`;
- archive SHA-256: `76b2842349093bb0f5c2bdc60995f78256d7cf6e2e4d64be84768a082450ceb1`;
- manifest count: 40 files;
- manifest verification on 2026-09-27: **40/40 exact SHA-256 PASS**;
- current frozen production coordinate: 335 players / 670 Y2-Y3 rows.

The historical research branch is no longer present as a live GitHub branch, but the exact archive contains a git bundle carrying commit `122e802...` and immutable tag `research-freeze/a2-burr-20260922`. The deployed production source also hard-codes the same model version, research commit, branch/tag identity, archive digest, current row counts, Stage-D shard digests, and distribution parameters.

No ancestor is accepted as a substitute for this candidate.

## Exact package semantics

### State probabilities
Frozen **A2** future-state probability primitive.

### Conditional state means
Frozen **Stage-D A2 handoff** state means.

### Within-state uncertainty
- QB Y2/Y3: **Burr XII M1**, mean-one ratio distribution.
- RB/WR/TE Y2/Y3: **direct-Gamma M1**, mean-one ratio distribution.

Frozen deployed parameters:

- QB Y2: Burr XII `c=4.412206982641597, m=1.517013117227367, d=1.7436570629747394, scale=1.135078009403411`;
- QB Y3: Burr XII `c=4.089640332906609, m=1.5671440102088534, d=1.811664290379622, scale=1.1566910766124239`;
- RB Y2: direct-Gamma shape `7.350891953014491`;
- RB Y3: direct-Gamma shape `7.728654304702037`;
- WR Y2: direct-Gamma shape `10.65922356483981`;
- WR Y3: direct-Gamma shape `10.37496771008586`;
- TE Y2: direct-Gamma shape `8.788467575558814`;
- TE Y3: direct-Gamma shape `9.024660406225102`.

No fitting, route selection, clipping, market input, post-hoc scaling, or replacement by D0/D1 is authorized.

## Exact historical evidence carried by the freeze

The verified archive contains:
- all 19 exact frozen A2 model files;
- all 19 exact Burr origin/horizon fits;
- `HISTORICAL_SELECTED_CHALLENGER_10894.csv`;
- `HISTORICAL_REPLAY_SCORECARD.csv`;
- `STAGE_D_CURRENT_MATERIALIZATION_335x2.csv`;
- `STAGE_D_SIMULATION_50000_ALL_ROWS.csv`;
- exact reference implementation;
- golden fixtures;
- manifest/provenance.

Historical coordinate:
- H2 origins 2014-2023;
- H3 origins 2014-2022;
- **10,894 exact rows**.

Current Stage D:
- 335 players;
- 670 Y2/Y3 rows;
- 50,000 simulation draws per row;
- 33,500,000 total draws;
- 670/670 mean-fidelity pass;
- zero runtime clipping.

## Historical uncertainty evidence preserved exactly

Against the package's historical direct incumbent/control comparison:
- pooled CRPS gain: **+0.8969055**;
- dependence-aware 90% lower replay: **+0.7200**;
- 10/10 pooled origins improve;
- QB CRPS gain: **+2.418856**;
- RB: **+0.929237**;
- WR: **+0.571551**;
- TE: **+0.538984**.

The package also preserves a real limitation:
QB Burr XII fails the frozen dense historical calibration checkpoints at **1.45x, 1.50x and 1.55x**. That limitation is not erased by current deployment and must remain visible in the symmetric audit.

## Comparability contract for this audit

The deployed candidate will be compared on exact common H2/H3 PIT/OOT rows wherever possible to:
- D1;
- N1 HistGB;
- N2 spline two-part;
- any other already-audited candidate only where exact common keys and compatible outputs exist.

Comparable dimensions when exact rows/outputs exist:
- expected-points MAE/RMSE/bias/rank;
- state/persistence Brier and log loss;
- CRPS;
- position/horizon/origin robustness;
- pairwise clustered uncertainty.

Distributional calibration beyond CRPS is compared only when both sides expose recoverable compatible quantiles/distributions. Otherwise the dimension is explicitly **uncomparable**, not treated as equal.

## Current end-to-end production boundary

This audit candidate is the **Y2/Y3 future-model package only**.

Y1 remains provider/source Forecast authority. The audit must not claim that a model-family comparison of Y2/Y3 establishes scientific authority for current-provider Y1 projections.

## No-model-shopping rule

This candidate is admitted after the original audit freeze solely because Management identified an omitted already-deployed package. It is not a newly invented challenger and does not reopen the bounded family slate.

Production Forecast / H3 / Intrinsic remain unchanged.
