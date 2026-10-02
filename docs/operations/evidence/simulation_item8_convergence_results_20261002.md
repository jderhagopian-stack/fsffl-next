# Simulation 2.0 item 8 — convergence / PIT closeout evidence

**Study status:** complete.  
**Production authority:** unchanged at **50,000 canonical runs**.  
**Successful workflow:** GitHub Actions run `36999960485`, head `9ec10864aca3a785baeab941d746fe114ca1ab36`.  
**Final artifact:** `simulation-item8-convergence-pit-final` / artifact `11224026589` / SHA-256 `8116d174d9d6aef5bd9fa3c292c513718d2a98b8037337ff4b40a4f9372dbae8`.

The pre-registered study executed eight independent roots, each with baseline, a clear common-world perturbation (+6/-6 weekly points), and a near-boundary perturbation (+0.5/-0.5), at 1k screening context plus governed 5k / 10k / 25k / 35k / 50k / 75k / 100k counts. The 100k result is a research reference only.

## Convergence versus same-root 100k reference

| runs | expected wins max-abs p90 | playoff max-abs p90 | title max-abs p90 | finish TV p90 | pick-slot TV p90 | 3-run bundle median |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5,000 | 0.056143 | 0.015639 | 0.015911 | 0.029759 | 0.031003 | not authority candidate |
| 10,000 | 0.038218 | 0.011375 | 0.010175 | 0.020938 | 0.020684 | 6.93 s |
| 25,000 | 0.023492 | 0.005944 | 0.003946 | 0.009894 | 0.010016 | 17.33 s |
| 35,000 | 0.017301 | 0.005057 | 0.003147 | 0.007244 | 0.007866 | 24.23 s |
| **50,000** | **0.014007** | **0.002964** | **0.002427** | **0.005272** | **0.005575** | **34.64 s** |
| 75,000 | 0.008059 | 0.002334 | 0.001093 | 0.003512 | 0.003481 | 51.86 s |
| 100,000 | 0 | 0 | 0 | 0 | 0 | 69.09 s |

The 1k row remains screening context only and is not a production-authority candidate.

## Counterfactual stability

At the production 50k count, all six tested scenario-delta sign comparisons matched the same-root 100k reference across **8/8 roots**:
- clear expected-wins delta;
- clear playoff-probability delta;
- clear championship-probability delta;
- near-boundary expected-wins delta;
- near-boundary playoff-probability delta;
- near-boundary championship-probability delta.

The near-boundary perturbation is intentionally small; its 100% sign agreement is sensitivity/stability evidence, not proof of causal historical accuracy.

At 50k, independent-root dispersion remained small:
- baseline expected wins: mean 6.929988, root SD 0.004624, range 0.01438;
- baseline playoff probability: mean 0.457615, root SD 0.002317, range 0.00732;
- baseline championship probability: mean 0.031445, root SD 0.000752, range 0.00216;
- baseline future-pick expected slot: mean 6.32229, root SD 0.011119, range 0.04002;
- clear and near scenario deltas retained 100% sign consensus across roots.

## Interpretation

The study supports the existing 50k production authority:
- 50k materially tightens the 35k error envelope while avoiding the roughly 50% higher study runtime of 75k;
- 75k and 100k continue to reduce Monte Carlo error, but the measured improvement is incremental rather than evidence that current 50k outputs are materially unstable;
- 35k is reasonably close in this fixture, but item 8 does not establish a product need or governance basis to reduce authority;
- no adaptive trial-count rule is justified by this single governed fixture.

Therefore **no production-count or adaptive-authority change is made**. Any future proposal to change 50k remains a separate Management decision and must receive explicit approval before implementation/promotion.

## PIT calibration closeout

The bounded existing-store audit found authentic 2026 prospective inputs:
- 364 canonical State snapshots across two leagues;
- 12 immutable provider ROS projection snapshots;
- 22,050 normalized projection observations;
- 6 prospective football-state captures;
- authentic pre-opener offense Forecast artifact 63, but without a retained matching State payload;
- earliest retained matched State+Forecast checkpoint after the opener: State `a7d56f...` plus Forecast artifact 87.

Final-season realized targets do not yet exist because the 2026 season is active:
- fully realized final-season Simulation calibration cases: **0**;
- scored probability observations: **0**;
- scored continuous observations: **0**.

Per Management's no-hunt correction, this is the closeout result rather than a prompt for archive discovery. Do not reconstruct old Forecasts, backfill current projections, scrape archives, or delay item 8 searching for data NEXT did not capture. The leakage-safe checkpoint/scoring framework remains ready for prospective scoring as current authentic checkpoints resolve.

Counterfactual alternate worlds remain validated by replay, convergence and sensitivity; they are not scored against unknowable causal historical outcomes.
