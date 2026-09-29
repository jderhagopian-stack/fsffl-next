# 2026-09-29 — Rolling FUMBLES_LOST authority corrective

## Management decision

The current Week-2-only first-party `FUMBLES_LOST` contract is too brittle for a low-impact, sparse scoring coordinate. It must not be allowed to block the entire current Forecast -> Simulation -> Intrinsic product path merely because canonical State advances beyond Week 2.

The existing first-party model remains the starting scientific authority:
- exact lost fumbles only;
- position-level lost-fumble rates;
- player role/opportunity evidence;
- non-zero uncertainty;
- no named-player tuning;
- no substitution of total fumbles;
- no contamination of unrelated Forecast coordinates;
- no fabricated preseason/PIT history.

## Required Research action

Run a **bounded rolling-cutoff validation**, not a broad Forecast-family search.

Determine whether the already accepted opportunity-rate model can be extended from the validated Week-2 snapshot to later completed-week cutoffs by updating the current-season opportunity sample with all completed weeks available at the canonical State.

At minimum:
1. freeze the rolling formulation before scoring;
2. evaluate later historical cutoffs where recoverable (e.g. Weeks 3, 4, 5 and additional practical in-season cutoffs) using chronology-preserving evidence;
3. preserve the frozen historical position lost-fumble rates and the accepted role-prior logic unless evidence requires a specifically justified rolling transformation;
4. do not retune from named 2026 outcomes;
5. quantify calibration/error/uncertainty by cutoff and position;
6. determine whether one rolling contract is supportable for the remainder of the season or whether a small number of governed cutoff regimes are needed;
7. keep uncertainty explicit and non-zero;
8. return the smallest defensible production contract.

## Materiality / downstream authority decision

`FUMBLES_LOST` is a supplemental, sparse, low-impact coordinate. Management directs that downstream product authority must distinguish **material** from **non-material** partial scoring coordinates.

Implementation must not silently substitute zero or pretend the coordinate is complete. However, a temporarily unavailable/non-authoritative `FUMBLES_LOST` estimate should not automatically block all Simulation/Intrinsic if its maximum plausible scoring impact is immaterial to the downstream use case.

Research must provide a bounded materiality rule or uncertainty-based impact bound suitable for downstream authority. The rule must be generalizable, not named-player-specific and not tuned merely to make acceptance pass.

## Boundaries

Do not:
- reopen general Forecast model-family selection;
- change Y2/Y3/Y4-Y7 Forecast authority;
- change K/DST authority;
- alter Intrinsic semantics;
- weaken exact lost-fumble target semantics;
- use total fumbles as a proxy;
- fabricate missing values;
- use Market/Owner/Team Utility feedback to tune Forecast;
- reopen #294/#295/#296 runtime architecture.

## Required handoff

Research must persist:
- rolling-cutoff validation design/results;
- accepted or rejected rolling update contract;
- uncertainty behavior;
- materiality rule for downstream authority;
- implementation acceptance tests;
- limitations.

If supported, Implementation may then:
- make the first-party current-season supplement advance automatically with canonical completed week;
- preserve provenance and completed-week metadata;
- invalidate/rebuild on State advance;
- treat unavailable FUMBLES_LOST as explicit non-material partial authority when the Research materiality gate says so;
- rerun the full hosted lifecycle acceptance on the existing #296 runtime lineage.

## Terminal condition

This directive is complete when Research either:
1. produces a defensible rolling/current-season FUMBLES_LOST authority and downstream materiality contract for Implementation; or
2. demonstrates that no such bounded contract is defensible and returns a genuine Management gate.
