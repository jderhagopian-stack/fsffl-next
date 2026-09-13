# Career-Persistence Feature Layer + Multi-Year Forecast V2 — Production Readiness

## Executive decision

**Decision: DO NOT PROMOTE.**

This workstream reached its predeclared stopping rule. A compact, Forecast-owned career-state layer was built and validated chronologically, but **no tested feature family added stable incremental value beyond the governed bounded career-transition baseline**. Development-only feature selection therefore selected **no features**, and the final untouched 2017–2022 holdout candidate is exactly the governed bounded control.

No production Forecast PR should be created from this result. PR #131 remains research provenance only. Model A economics were not changed and no Model B work was started.

This result does **not** mean age, pedigree, role, availability, efficiency, or QB mobility are inherently irrelevant to career forecasting. It means the small, readily available proxies tested here did not support a safe incremental mean/survival correction under the governed chronological design. The strongest evidence from this cycle is negative: this particular enrichment layer should not be promoted.

## Scope and architecture

The tested architecture remained within the existing authority boundary:

raw public/historical football evidence → offline normalization → point-in-time player-season features → compact Forecast-owned career-state features → governed career-transition calibration/materializer → Year-2 / Year-3 Forecast distributions.

No dynasty Market Value, Team Utility, owner behavior, named-player rules, QB bonuses, superstar bonuses, proprietary dynasty rankings, or live play-by-play scans were used.

The live request path was intentionally designed to consume only precomputed derived features and versioned coefficients. Because the candidate failed and is not promoted, **production storage, cache, memory, and request-latency impact are zero**.

## Sources evaluated and commercial-use posture

| Source / evidence | Fields or purpose | PIT/historical depth | Commercial-use posture | Decision |
|---|---|---|---|---|
| Existing governed PR #131 career-transition panel | fantasy production, position, age/experience, next-season survival/production | 1999–2024; already reconstructed for chronological research | Internal governed evidence derived from the repository's existing pipeline | Used |
| nflverse seasonal player statistics | games, passing attempts, carries, targets, passing/rushing/receiving yards | Annual player seasons; fetched offline by season | nflverse data licensing requires source-specific attribution/terms; the selected stats path is suitable for offline research and a future attributed commercial pipeline, subject to retaining required notices | Used |
| nflverse player metadata | draft pick/round and UDFA proxy | Historical player metadata | Same source-specific attribution/terms discipline as nflverse data | Used |
| Historical contracts/team commitment | possible QB/job-security signal | Potentially useful but PIT reconstruction and source provenance are materially more complex | No clean need to introduce this dependency for v2 | Rejected from v2 |
| Historical depth charts | role/job-security signal | Historical comparability is weaker; source coverage changed after 2024 | Avoided rather than introduce a brittle dependency | Rejected from v2 |
| Detailed injury history | availability/durability | Sparse/heterogeneous across long history | Games played already supplies a simpler PIT availability proxy | Rejected from v2 |
| Direct starts | starter continuity | A stable cross-era player-level starts field was not present in the chosen seasonal source | QB role was instead proxied transparently by top-32 seasonal pass-attempt status | Not used directly |
| Expected fantasy points / proprietary micro-metrics | opportunity quality / efficiency | Varies materially by provider | Not necessary for this bounded v2; avoided extra licensing/provenance complexity | Rejected from v2 |

The research intentionally stores only governed derived fields if a feature is promoted. Raw annual source files are an offline ingestion concern, not a live application dependency.

## Point-in-time feature candidates

Five coherent families were predeclared and tested one family at a time on development seasons only:

- **Pedigree:** draft-pick percentile, undrafted indicator.
- **Availability:** games played as a share of the season maximum, plus a two-season availability mean.
- **Role/stability:** position-season opportunity percentile; two-season role mean; one-year role volatility; for QB, accumulated established-starter seasons using a top-32 pass-attempt proxy.
- **Efficiency:** fantasy production per opportunity.
- **QB mobility:** rushing yards as a share of passing-plus-rushing yards.

Opportunity was deliberately simple and cross-era stable: QB pass attempts; RB carries + targets; WR/TE targets.

The enriched candidate used a transparent per-position linear residual adjustment to the governed conditional-production multiplier and survival probability. It retained empirical transition bounds, probability bounds, the position training ceiling, recursive uncertainty carry-forward, and deterministic versionable calculations. It did not add a new model family or a black box.

## Chronological design and evidence-contract repair

Feature selection used **2005–2016 development seasons only**. The final holdout was **2017–2022** and was not used to choose feature families.

A first plumbing workflow proved the source join and end-to-end workflow, but inspection found a genuine evidence-contract defect: its control path used a mean-of-ratios transition estimate rather than FSFFL's governed empirical-Bayes calibration in `scripts/run_career_calibration.py` (through-origin conditional-production slope plus shrinkage). That first run is **non-authoritative**.

The one management-authorized narrow repair replaced only that calibration implementation. Feature definitions, chronological split, family-selection criteria, model form, and final acceptance gates remained frozen. The final valid run therefore uses the same governed calibration primitives as the existing Forecast research.

## Predeclared acceptance standard

The enriched materializer had to satisfy all of the following without holdout tuning:

1. Year-2 MAE at least 2% better than governed bounded and carry-forward.
2. Year-3 MAE no more than 1% worse than governed bounded.
3. Cumulative MAE at least 3% better than governed bounded and carry-forward.
4. At least 60% of holdout folds better than bounded, with no fold harmed by more than 10%.
5. All-QB cumulative MAE no more than 2% worse than carry-forward.
6. Elite-QB cumulative MAE at least 10% better than the failed bounded materializer.
7. RB/WR/TE cumulative MAE each within 5% of bounded.
8. Nominal 80% uncertainty coverage between 70% and 90% for Year 2 and Year 3.
9. Survival Brier below 0.25 and better than bounded for both horizons.
10. Zero pathological trajectory-bound violations.

Development-only feature-family inclusion additionally required either at least a 0.5% overall cumulative gain or 1% QB cumulative gain, with no position harmed by more than 3%.

## Development-only incremental feature value

No family cleared the frozen development gate:

| Family | Overall cumulative change vs governed baseline | QB cumulative change | Worst positional harm | Decision |
|---|---:|---:|---:|---|
| Availability | -91.70% | -109.61% | 109.61% | Reject |
| Efficiency | -54.90% | -42.51% | 62.45% | Reject |
| Pedigree | -26.46% | -30.86% | 30.86% | Reject |
| Role/stability | -75.08% | -93.44% | 93.44% | Reject |
| QB mobility | -26.08% | -28.47% | 28.47% | Reject |

Negative percentages above mean the candidate's error was worse, not better.

The large deterioration is useful diagnostic evidence: these state variables are not safe as simple additive linear residual corrections to the governed transition path. Their proxies may still contain information, but the current model form compounds noisy cross-era state corrections rather than extracting reliable incremental persistence.

**Final selected feature set: none.**

## Final untouched holdout results

The 2017–2022 holdout contains **4,508** complete player/fold observations. Because no development-tested feature family was accepted, the final enriched candidate equals the governed bounded baseline by construction.

| Forecast | Year-2 MAE | Year-3 MAE | Cumulative MAE |
|---|---:|---:|---:|
| Carry-forward | 41.567 | 43.325 | 102.423 |
| Governed bounded | 42.442 | 41.188 | 101.563 |
| Enriched v2 | 42.442 | 41.188 | 101.563 |

Therefore:

- Year 2: FAIL; enriched is not 2% better than bounded or carry-forward.
- Year 3: PASS safety; no degradation versus bounded.
- Cumulative: FAIL; no improvement versus bounded and only ~0.84% better than carry-forward, below the 3% gate.
- Fold stability: FAIL; 0/6 holdout folds beat bounded because the selected candidate ties it exactly.
- Worst-fold guardrail: PASS; no additional harm versus bounded.

Governed bounded/enriched cumulative MAE by final holdout source season:

| Source season | n | Cumulative MAE |
|---|---:|---:|
| 2017 | 717 | 93.749 |
| 2018 | 739 | 89.944 |
| 2019 | 749 | 98.708 |
| 2020 | 755 | 99.621 |
| 2021 | 765 | 106.590 |
| 2022 | 783 | 120.190 |

This six-season final holdout is an incremental-enrichment test. It does not supersede the canonical 18-fold materializer production-readiness report; it answers the narrower question of whether the compact state layer adds robust new information.

## QB results

### All QB

| Forecast | Cumulative MAE |
|---|---:|
| Carry-forward | 180.744 |
| Governed bounded | 180.248 |
| Enriched v2 | 180.248 |

The all-QB safety gate passes only because development selection rejected every added family; there is no incremental QB gain.

### Elite QB

The elite-QB holdout contains **269** observations.

| Forecast | Cumulative MAE |
|---|---:|
| Carry-forward | 258.392 |
| Governed bounded | 258.598 |
| Enriched v2 | 258.598 |

The required 10% improvement versus the failed bounded elite-QB path is not present. **Elite-QB persistence remains unresolved.** The attempted football-state proxies do not justify a manual elite-QB rule, QB bonus, or hidden correction.

## RB / WR / TE safety

| Position | Carry cumulative MAE | Governed bounded | Enriched v2 |
|---|---:|---:|---:|
| RB | 104.739 | 101.802 | 101.802 |
| WR | 93.197 | 94.750 | 94.750 |
| TE | 66.843 | 71.301 | 71.301 |

The non-QB safety gate passes because the final candidate equals the bounded control. There is no evidence-supported enriched improvement to promote.

## Survival, uncertainty, and trajectory safety

For the final enriched/bounded holdout:

- Year-2 survival Brier: **0.1959** — below 0.25, but not improved versus bounded, so the incremental gate fails.
- Year-3 survival Brier: **0.2548** — above the 0.25 gate and not improved versus bounded; FAIL.
- Nominal 80% Year-2 coverage: **83.05%**; PASS.
- Nominal 80% Year-3 coverage: **83.47%**; PASS.
- Pathological trajectory-bound violations: **0**; PASS.

The prior recursive uncertainty carry-forward remains important: uncertainty is not the reason this v2 fails. The unresolved problem is incremental mean/survival information, especially durable role/persistence at deeper horizons.

## Operational footprint

Final valid workflow measurements:

- Derived rows: **14,301**.
- Derived feature-table size: **1,678,999 bytes (~1.60 MiB)**.
- Offline preprocessing time on GitHub Actions: **6.79 seconds**.
- Full local read of the derived table: **~1.43 ms**.
- Planned refresh cadence: annual/offline; a current-season role refresh could occur after regular-season data stabilizes.
- Planned live path: precomputed derived features + versioned coefficients; no raw historical scan.

The workflow did not retain an aggregate byte count for every temporary raw annual download, so an exact raw-source-volume total is not claimed. That is an observability limitation of this failed research candidate, not a production performance risk. The persisted derived table is only 1.60 MiB, and because nothing is promoted, **actual production storage/runtime/cache impact is zero**.

## Bounded diagnostic and stopping decision

The failure is not primarily a compute, storage, or architectural-cost problem. The proposed feature layer is operationally cheap. The problem is evidence quality and model fit:

- **Data/proxy quality:** top-32 pass attempts and coarse opportunity percentiles are transparent but imperfect proxies for starter security and team commitment.
- **Cross-era comparability:** role/opportunity signals can mean different things across eras and offensive environments.
- **Model form:** a linear residual correction to already-governed recursive transitions materially overcorrected on development data.
- **Missing state:** contract/team commitment or richer role context could contain information, but the clean PIT historical evidence was not strong enough to justify adding those dependencies in this bounded v2.
- **Irreducible uncertainty:** prior persistence research already showed weak player-specific persistence discrimination. This cycle does not overturn that finding.

The only warranted implementation repair was the governed-calibration correction described above, and it has been used. The corrected study still fails before any holdout-driven tuning. Under the management stopping rule, **do not start another feature-combination tournament or another model family in this workstream**.

## Reproducibility

Authoritative final workflow:

- Workflow: `Career Persistence Feature Layer Research`
- Run: **34747294652**
- Head: `b6efe7743462c66631af6b7ab452aaecd65def89`
- Artifact: **10314488088**, `career-persistence-feature-layer-research`
- Artifact SHA-256: `37e1cc2d0fe02134488ecdeaed64fce3a3bb8432f07bb5357989d0b8b96d1a3b`
- Repository tests: **1,153 passed, 2 warnings** (existing Pydantic deprecation warnings)

The earlier workflow run `34747119086` is retained only as plumbing provenance and must not be used as final evidence because its control calibration was inconsistent with the governed career calibration.

## Production recommendation

**DO NOT PROMOTE.**

Do not create a production Forecast PR from this v2. Do not change Model A economics. Do not add a manual QB/elite-QB premium. Preserve the negative result and the compact-source architecture as research provenance.

The practical conclusion is narrower than “football-state features do not matter”: the readily available, commercially tractable proxies tested here **do not provide enough stable incremental signal in this transparent enriched materializer to justify authoritative deep-horizon Forecasts**. A future workstream would need genuinely better point-in-time role/job-security evidence or a separately justified modeling approach, not more combinations of these same weak proxies.
