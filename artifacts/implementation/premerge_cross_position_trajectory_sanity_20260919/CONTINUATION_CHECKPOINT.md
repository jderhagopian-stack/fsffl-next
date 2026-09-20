# FSFFL NEXT - Pre-merge cross-position trajectory sanity continuation

Date: 2026-09-19

## Durable starting state

- PR: #147 (`implementation/forecast-intrinsic-i1-shapley`)
- Starting PR head: `d8a68fa171c0a40fdc1011f96231ed0df7247dda`
- Protected main/base: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- Research evidence head: `740bf845f287d1f050eab68f835472ccf401bab3`
- Diagnostic-head workflows confirmed successful: CI run 35466459963; Private-beta Intrinsic live diagnostics 35466459972; Build private-beta I1 activation artifacts 35466459961.

## Evidence generation

- Current cohort source: frozen 335-player P0 board, `source_percentile >= 0.90` within source-season x position concept.
- Current top-decile cohort size: 33 (QB 6, RB 9, WR 12, TE 6).
- Historical selection evidence: frozen 2014-2020 prediction artifact, 10,336 rows total across 2014-2022 artifact; only 2014-2020 used for selection/support bands.
- 2021-2022 is descriptive replication only.
- No refit, retrain, retune, route change, scoring change, runtime/model code change, merge, or deploy performed.

## Final classification

**HOLD - MANAGEMENT ACCEPTANCE OF RB UNCERTAINTY REQUIRED**

The artifact commit containing this checkpoint is the durable continuation checkpoint. Its exact commit SHA is intentionally verified externally after commit creation because a Git commit cannot contain its own SHA.