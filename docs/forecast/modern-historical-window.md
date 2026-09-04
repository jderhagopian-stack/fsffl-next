# NEXT-2 Modern Historical Forecast Window

## Decision

The primary empirical calibration window for the first production-grade NEXT-2 forecast study is **2019-2025**.

Older 2012-2014 multi-source archives remain useful as supplemental evidence and as a validation corpus for the ingestion/benchmark machinery, but they should not determine modern source weights by themselves when newer point-in-time evidence can be recovered.

## Why 2019-2025 is primary

This window gives NEXT-2 seven modern NFL seasons and is more representative of the environment in which current dynasty decisions are made. It should therefore carry more authority than much older data when source skill has changed over time.

The benchmark should retain older seasons for stability checks, but model-selection and production-weight promotion should emphasize recent held-out performance rather than treating every historical season as equally informative.

## Current modern evidence recovered

### NFL Fantasy

Historical projection pages are still addressable for prior seasons, including 2019 and 2025 season/week projection views. These pages expose projected passing, rushing, receiving, and fantasy-point fields. Each historical snapshot still needs a defensible availability timestamp and rights review before retained data enters the governed benchmark.

### FFB2022 public archive

A public 2022 research repository contains retained provider-specific QB projection files for CBS, ESPN, NFL, and Yahoo, plus a FantasyPros 2021 RB distribution artifact. Repository commit history shows the files were present in 2022, which makes this a useful modern point-in-time recovery lead. Coverage is incomplete, so it is evidence for acquisition and adapter testing rather than a sufficient full benchmark on its own.

### FantasyDataPros 2023 retained projections

A public FantasyDataPros course-data repository retains a dated **FantasyPros 2023 preseason full-stat projection file** named `01-Fantasy Pros Projections - (2023.08.17).csv`. The artifact includes player/team/position plus passing attempts, completions, passing yards, passing touchdowns, interceptions, rushing attempts/yards/touchdowns, receptions, receiving yards/touchdowns, and fumbles lost. This is exactly the raw-stat shape NEXT-2 prefers because league fantasy points can be derived later from canonical league rules rather than inherited from a provider scoring system.

The repository README states that its course datasets are free to use, but upstream FantasyPros data rights remain a separate governance question. Treat the artifact as a strong **private-research acquisition candidate** and point-in-time/schema proof; do not assume that the upstream table may be redistributed or commercialized merely because the teaching repository is public.

### ffanalytics / FantasyFootballAnalytics

The modern ffanalytics project supports seasonal and weekly scraping from multiple projection sources including CBS, ESPN, FantasyPros, FantasySharks, FFToday, NumberFire, FantasyFootballNerd, NFL, RTSports, and WalterFootball. Its maintainers explicitly note that historical periods cannot simply be recreated by running today's scraper with an old year/week. This confirms the need to recover retained snapshots, archives, commit history, or provider-supported historical queries instead of backdating live data.

### Older FantasyFootballAnalytics archive

The retained 2012-2014 files confirm that multiple providers historically published comparable raw stat projections. They are useful for architecture validation, but they are supplemental to the 2019-2025 priority window.

## Acquisition objective

Recover as much of 2019-2025 as possible across at least **3-5 genuine projection sources**. Prefer sources that supply raw football-stat projections because they can be scored independently of any one league scoring system.

The acquisition work should proceed in parallel across providers. A provider should enter the scored modern cohort only after:

1. the historical artifact is demonstrably tied to the relevant season/week or has a conservative point-in-time availability timestamp;
2. the projection fields are understood and normalized;
3. player identity can be matched to the realized-outcome backbone;
4. the intended private research use has been reviewed sufficiently for the acquisition method; and
5. source dependence/aggregation overlap is documented.

## Benchmark weighting across time

The initial study should report performance by season as well as pooled performance. Recent out-of-sample seasons should have greater relevance to production promotion than much older seasons.

Do not introduce an arbitrary recency coefficient. First measure year-to-year source stability. If recency weighting improves held-out forecasting, estimate and validate that behavior from the historical panel; otherwise retain a simpler scheme.

## Practical first milestone

The first modern benchmark does not require perfect 2019-2025 completeness. Run it once at least three genuine sources have defensible overlapping modern history and enough player/position coverage to support a meaningful held-out comparison. Add further seasons and sources through the same adapters without redesigning the benchmark.

## Non-negotiable point-in-time rule

A current projection page is never evidence of what a provider projected in a prior season. Historical calibration may use only retained dated artifacts, provider historical queries, archive captures, contemporaneous repository snapshots, or similarly defensible evidence of what was available at the time.
