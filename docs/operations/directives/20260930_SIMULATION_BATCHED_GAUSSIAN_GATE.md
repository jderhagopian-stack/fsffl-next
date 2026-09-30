# Management Gate — Versioned batched Gaussian Simulation kernel

**Status:** Management approved the versioned experimental implementation and predeclared study on 2026-09-30. Production adoption, merge to main, and deployment remain unauthorized pending a separate Management decision.

## Evidence from the current NEXT kernel

Fixture: the production regular-season kernel, 12 teams, 14 weeks, 84 matchups, six-team championship bracket, 50,000 trials, seed `20260905`, Python 3.12.14.

- Current exact-output-preserving local optimization: bind `max` once outside the regular-season loop. Two interleaved paired runs measured 5.908/5.589 s before and 5.708/5.399 s after; medians 5.749 s → 5.554 s (-3.4%). Full output is unchanged (SHA-256 `942c9d11c3375b8752762e652b953ca0f2c64651a364002e0458ff4f86e7c240`).
- Gaussian isolation, two interleaved paired runs: full kernel 6.148/5.725 s (median 5.937 s); replacing `Random.gauss(mu, sigma)` with `mu` while retaining every call site and all other kernel loops took 2.443/2.343 s (median 2.393 s). The measured Gaussian-generation delta is 3.543 s, 59.7% of the isolated full run. This is an attribution experiment only; the stub is not a candidate implementation.
- Profile count confirms the fixture issues 8.9M Gaussian calls: 8.4M regular-season scores plus 0.5M playoff scores. cProfile's profiled run records `gauss` at 6.068 s self / 9.292 s cumulative over 15.977 s total; instrumentation overhead makes those timings unsuitable as ordinary wall time.
- A bounded NumPy 2.3.5 `default_rng().normal` batch generated 8.4M draws (10,000 trials × 168 score draws × 5 batches) in 0.173 s, 48.5M samples/s, with a 12.82 MiB output batch and 48,784 KiB isolated-process peak RSS. An 8.9M scalar Python `Random.gauss` loop took 3.581 s. This is approximately 20.7× faster for the isolated draw-generation layer, with different random worlds. Extending the measured batch rate to 8.9M gives ~0.184 s.
- Holding the measured non-Gaussian kernel work at 2.393 s gives a first-order estimate of 2.58 s total for a vectorized kernel (about 2.3× the 5.94 s isolated current kernel, or about 2.15× the 5.55 s exact-optimized paired median). This is a ceiling-style projection for the kernel only; it excludes conversion, downstream aggregation, sorting, memory pressure, and full refresh work. It is not a production benchmark or promised result.
- Render is back online. `fsffl-next-private-beta` (free plan, one Virginia instance) currently runs the #310 `69e5a0d807e866f2d725d6ee74654f40ab5d54bd` deployment. Recent app startup was healthy with readiness `forecast=True simulation=True value=True complete=True`, startup RSS 318,128,128 B, peak RSS 322,514,944 B, runtime budget 429,496,720 B. Render metrics through 15:13Z showed memory 286–351 MB against 536.9 MB and CPU idle after startup. This is idle telemetry; no new Simulation refresh was triggered for this measurement.

The predecessor `sleeper-league-data/script/run_fsffl_season_simulator_preproduction.py` demonstrates batching but has different player availability/substitution, RNG consumption and model pathways. It is evidence for a performance pattern only.

## Approved experimental change (not production adoption)

Replace sequential calls to `random.Random.gauss` for weekly team score draws with bounded batches from a versioned NumPy normal generator. Preserve `Normal(mean_points, stddev_points)`, nonnegative floor at zero, independent per-team/week draws, current weekly scoring inputs, existing standings tie-break rules, seeded playoff bracket, six-team outcomes, all 50,000 trials, output fields, downstream authority, and all Forecast/Value/Decision semantics.

The random samples and simulation universes will differ from the current Python stream. Draw ordering is explicitly allowed to change only for this approved kernel version. No reduced precision, fewer trials, altered distributions, common-random-number assumptions, changed correlation, reduced tail fidelity, or changed Simulation authority is part of this proposal.

### Deterministic replay and persistence versioning

Current persisted Simulation identifies its model via `SIMULATION_MODEL_VERSION`, stores the result seed/count, and keys the artifact by State and Forecast fingerprint; it does not independently declare the RNG/kernel protocol. A new kernel therefore requires an explicit identity field and cache-contract version before rollout:

- Keep model semantics version distinct from execution protocol. Add a value such as `simulation_rng_protocol = "fsffl-numpy-pcg64-normal-v1"` to the request/result/artifact identity.
- Record root seed, seed-derivation protocol and separate regular-season/playoff stream IDs, trial count, State ID, Forecast fingerprint, compiled schedule/scoring fingerprint, NumPy version, BitGenerator name, dtype, batch layout/order, and kernel protocol in the persisted replay manifest.
- Derive deterministic independent regular-season and postseason streams from the root seed using a fixed documented derivation. Do not let batch size, worker count, or scheduling alter the stream mapping within protocol v1.
- Include kernel protocol and RNG protocol in cache fingerprints and `SIMULATION_MODEL_VERSION` so old artifacts cannot be mistaken for new replay-compatible results.
- Keep a v1 replay path (Python `Random.gauss`) for saved v1 manifests. Pin NumPy/BitGenerator behavior and validate repeated v1 runs in the supported deployment image. A replay manifest whose engine version is unavailable must report that version as unavailable, not silently regenerate with a different RNG.
- Keep production count exactly 50,000. Store no per-trial full score cube; process bounded batches and retain only required aggregate distributions plus bounded replay identity if that later work is separately designed.

## Required validation before production adoption

Management approval authorizes only an experimental branch and equivalence study. It does not authorize deployment. Pre-register this validation before running it:

1. **Deterministic protocol:** same manifest and supported runtime reproduce identical new-protocol output digest. Batch size, chunk boundary and worker scheduling changes either preserve samples exactly or are separately versioned. Verify old v1 replay continues to reproduce the saved v1 digest.
2. **Trial design / power:** use at least 100 independent root seeds × 50,000 trials per engine on identical captured State + Forecast inputs; increase the seed count if pre-study power analysis cannot bound all predeclared margins. Compare across independent seeds; do not treat same numeric seed across different algorithms as common random numbers.
3. **Player and team scoring distributions:** compare weekly and season means, standard deviations, calibration/coverage, CDF distance, and 1st/5th/50th/95th/99th percentiles. Test both input scoring distributions and all observable downstream player projections; the kernel itself accepts team distributions, so a player-level claim must be validated through the full product pipeline.
4. **Standings:** compare each team's expected wins, all rank probabilities and expected finish, rank-order distribution, tie behavior, and playoff qualification odds. Use predeclared two-one-sided equivalence tests (TOST) / bootstrap confidence intervals over seed replicates. Initial probability margin proposal: ±0.002 absolute for ordinary per-team probabilities, ±0.001 for expected wins, and ±0.005 for rank-distribution total-variation distance; Management must accept or revise margins before data collection.
5. **Playoffs/title:** compare round outcome and championship probabilities for every team, including seed/tiebreak paths; use the same probability margins and report confidence intervals and per-seed differences.
6. **Tails and uncertainty:** compare per-player/team 1%, 5%, 95%, and 99% quantiles, exceedance probabilities at decision-relevant thresholds, tail conditional means, Monte Carlo standard errors, interval coverage, and extreme-event frequency. Require no material tail undercoverage or rank reversal of the largest decision-relevant risks.
7. **Downstream decisions:** run Value, Team Utility, Decision, Search/Optimization and Analytics on both Simulation result sets. Compare selected options, decision sign/direction, candidate ranking and confidence/uncertainty, not just headline means. Any systematic changed decision behavior blocks adoption even if marginal distributions pass.
8. **Resource and usability:** benchmark full 50k kernel and full intelligence refresh on the free Render instance, including peak RSS under concurrent foreground navigation. Test batch sizes (e.g. 2k, 5k, 10k) and retain a hard measured headroom below the 536.9 MB service limit. Hosted run must complete and publish usable Forecast, Simulation, Value and downstream capabilities without restart or permanent partial readiness.
9. **Reporting:** publish per-seed outputs, all confidence intervals, distribution plots/tables, runtime and peak-memory data, replay-manifest examples, and exact model/cache protocol changes. No aggregate-only or selectively omitted tail reporting.

## Management decision already recorded

Management explicitly approved only the following experimental work:

- a versioned, non-bit-identical RNG stream for new Simulation generations;
- NumPy/PCG64 batched normal draws at 50,000 trials, subject to the validations above;
- a separate engine/RNG identity in persistence/cache and a retained v1 replay implementation;
- the predeclared equivalence margins above, or replacement margins before data collection.

Production remains on the bit-identical Python RNG path. The experimental branch must remain a draft and may not merge or deploy until a separate production-adoption decision.


## Experimental evidence — 2026-09-30

The exact executable study is archived as [`simulation_rng_equivalence_study_20260930_full.json.gz`](../evidence/simulation_rng_equivalence_study_20260930_full.json.gz). The compact report is alongside it. It contains 100 independent root-seed labels × 50,000 trials per engine, per-seed team outcomes/rank probabilities/tail summaries, and the pooled fixed-threshold score-CDF comparison. Per-trial arrays/histogram counts are not retained; the study streams each run into bounded in-memory arrays and persists per-seed results plus pooled CDF/interval summaries.

- Environment: Python 3.12.14, NumPy 2.3.5; batch size 500.
- Full observed-kernel median: Python RNG 5.700 s, NumPy/PCG64 2.718 s (2.097×). A fresh-process resource-only run measured 5.215 s vs 2.483 s (2.10×). This is isolated kernel evidence, not a hosted full-refresh timing.
- Fresh-process peak RSS: Python 41,644 KiB; NumPy batch 500 45,212 KiB (+3,568 KiB); batch 2,000 51,312 KiB (+9,668 KiB). This measurement shares NumPy import residency and does not represent full Render RSS. Batch 500 becomes the experimental default because it retained the measured speed while using less batch memory.
- All 36 predeclared per-team playoff/first-place/championship probability checks passed their ±0.002 margins. All 12 rank-distribution TV upper bounds passed ±0.005; the worst was 0.004637. Expected-wins order was identical (0 pairwise inversions).
- All 12 expected-wins equivalence checks **failed to establish equivalence** within ±0.001. Every simultaneous interval crossed the margin; the intervals included zero. Team t04 had observed difference +0.002395 wins and simultaneous interval [-0.002201, +0.006991]. This is inconclusive, not evidence of a systematic change; do not relax the approved margin based on this result.
- Team season-score pooled empirical CDF distance was at most 0.000772; its simultaneous 95% DKW upper bound was at most 0.002429. Per-team season-point means, standard deviations, quantiles (1/5/50/95/99%), tail conditional means, fixed input-derived exceedance probabilities, and Monte Carlo uncertainty are all included in the archived report. No held-out historical outcome coverage test was run.
- Full-runtime 50k regression confirms exact replay for the same experimental manifest, unchanged player Forecast rows, and unchanged Team Utility position-strength / roster-resilience inputs used by Search. The study does **not** run paired changed-State Decision/Search/Optimization candidate-set evaluation; this remains a production-adoption blocker.
- The experimental stream changes random universes by design. The legacy Python path remains the default and its cache identity is unchanged.
- After the statistical runs, explicit BitGenerator (`PCG64`), `float64`, and draw-layout fields were added as metadata only. A 50k full-result replay audit confirms identical output for the same manifest; the numerical draw/aggregation path was not changed by those labels.

No experimental path was deployed. Render still serves #310 `69e5a0d807e866f2d725d6ee74654f40ab5d54bd`; the prior physical peak was 524.7 MB / 536.9 MB. A hosted concurrent-refresh memory trial remains unrun.
