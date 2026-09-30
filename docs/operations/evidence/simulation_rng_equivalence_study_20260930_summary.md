# Experimental Simulation RNG study — 2026-09-30

**Decision status:** research result only. Production remains on `python-random-gauss-v1`. Management approval covered this experiment and study; it did not authorize merge to `main`, deployment, or production adoption.

## Study and replay identity

- Same captured 12-team, 14-week, 84-game, six-playoff-team fixture; 50,000 trials per run.
- 100 independent root-seed labels (`20261001`–`20261100`) for each engine. Numeric labels match, but the two RNG algorithms are separate streams, not common-random-number pairs.
- Runtime: Python 3.12.14, NumPy 2.3.5, NumPy batch size 500.
- Model behavior held fixed: Normal(mean, standard deviation) score draws, independent team/week inputs, zero floor, scoring inputs, standings/tie rules, seeded Python playoff stream, 50,000 trials, result fields, and Simulation authority. The generated random universes differ.
- The result and persisted cache identity explicitly distinguish RNG protocol, runtime version, BitGenerator, float dtype, draw layout, effective batch size, root-seed derivation, and simulation-input fingerprint; the experimental Simulation model/cache version is separate. The established Python cache key remains unchanged.
- The 100-seed statistical run preceded the final addition of explicit BitGenerator/dtype/layout labels; those fields are descriptive and did not alter draws, ordering, aggregation, or numeric results. A post-study full 50k replay audit records both protocol identities and complete result digests in the archive.
- The compressed detailed record contains every root-seed team outcome, rank vector, per-seed score/win/tail summaries, and pooled score-CDF results. SHA-256: `e23d105ce9110e5ec25d0d6c6e922491ae4b7addbd2ab5f8e71e910b10556aaa`.

## Measured runtime and memory

| Measurement | Python `Random.gauss` | NumPy PCG64 batch 500 | Result |
|---|---:|---:|---:|
| 100-seed observed-kernel median | 5.700 s | 2.718 s | 2.097× faster |
| Fresh-process kernel | 5.215 s | 2.483 s | 2.10× faster |
| Fresh-process peak RSS | 41,644 KiB | 45,212 KiB | +3,568 KiB |

A 2,000-sample batch took 2.575 s and peaked at 51,312 KiB (+9,668 KiB). The 500 batch had a slightly lower measured peak and essentially the same speed, so it is the experimental default. The RSS harness imports NumPy for both engines; these deltas estimate batch allocation under shared NumPy residency. They are not full-app or Render measurements.

The historical physical peak on Render was 524.7 MB against a 536.9 MB limit, leaving about 12.2 MB. The 500-batch local increment would consume roughly 3.5 MB if additive, but this is an inference, not hosted evidence. The experiment was not deployed and Render was not stressed.

## Predeclared equivalence results

| Check | Result | Status |
|---|---|---|
| Per-team playoff, first-place, and championship probability, margin ±0.002 | All 36 simultaneous intervals fit inside the margin; largest absolute point difference 0.000624 | Pass |
| Per-team rank-distribution total variation, margin ±0.005 | All 12 conservative upper bounds pass; worst 0.004637 | Pass |
| Expected wins, margin ±0.001 | All 12 intervals cross the equivalence margins. The intervals include zero. Team `t04`: difference +0.002395 wins; simultaneous 95% interval [-0.002201, +0.006991]. | **Inconclusive; not equivalent yet** |
| Expected-wins team ordering | Identical order, zero pairwise inversions | Pass for this fixture |
| Season-score empirical CDF | Maximum observed 256-bin distance 0.000772; simultaneous 95% DKW upper bound 0.002429 | Reported; no numeric CDF acceptance margin was predeclared |
| Score tails and uncertainty | Per-team means, standard deviations, 1/5/50/95/99% quantiles, bottom/top 1% and 5% conditional means, fixed input-derived ±2/3 SD exceedance rates, and MCSEs are reported with simultaneous intervals | Measured; no numeric tail-equivalence margins were predeclared |
| Player Forecast and Search inputs | Exact same Forecast rows, position-strength evidence and roster-resilience evidence through the full-runtime 50k builder | Pass for these unchanged inputs |
| Decision / changed-State Search / Optimization outcomes | No paired changed-State candidate-set study was run | **Not evaluated; blocks adoption** |
| Historical outcome coverage | No held-out observed-outcome calibration/coverage evaluation in this RNG-kernel study | Not evaluated |
| Hosted free-Render full-refresh concurrency and RSS | No experimental deployment or refresh was made | Not evaluated |

The expected-wins result is inconclusive rather than proof of a systematic change: its confidence intervals include zero, but they are too wide to fit within the approved ±0.001 margin, and one observed point difference is outside that margin. Keep the predeclared margin intact. Management must decide whether to extend the independent-root study, define an approved more efficient equivalence design, or stop the experimental path.

## Regression and operating status

- Full-runtime 50k regression confirms identical replay output for the same experimental manifest.
- Legacy and experimental full-runtime builds preserve identical player Forecast projections, position-strength rows, roster-resilience inputs consumed by Search, and tested Team Utility classifications for the fixture.
- Focused test function and Python compilation pass locally. Local `pytest` is unavailable; exact-head GitHub CI status must be checked before returning the draft PR.
- Render `fsffl-next-private-beta` still serves main commit `69e5a0d807e866f2d725d6ee74654f40ab5d54bd` (#310). No experimental code is deployed.

**Adoption recommendation:** do not adopt or deploy yet. The study supports a material kernel speed improvement and passes the probability and rank margins, but it does not establish expected-wins equivalence or downstream decision/search/optimization equivalence, and it has no hosted free-tier resource evidence.
