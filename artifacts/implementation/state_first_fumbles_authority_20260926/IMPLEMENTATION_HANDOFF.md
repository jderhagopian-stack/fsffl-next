# FSFFL NEXT — State-first / FUMBLES_LOST Authority Handoff

Updated: 2026-09-26 UTC

## Terminal state

**MANAGEMENT GATE — FORECAST / PRODUCT IMPLEMENTATION — EXISTING-FSFFL FULL-CAPABILITY ACCEPTANCE CONFLICTS WITH CURRENT FUMBLES_LOST AUTHORITY**

The State-first league-sync / reuse-or-rebuild / truthful-readiness implementation is complete. The remaining acceptance failure is not a State-orchestration defect and cannot be cleared by additional implementation without changing Forecast authority or supplying qualifying evidence.

## Implemented State-first contract

Canonical main already contains the bounded corrective:
- PR #246 — State-first sync, reuse-or-rebuild, truthful capability readiness; merge `d19990ad6388e822b5a31e03be5cd2b4ea38c6a9`.
- PR #249 — in-service State-first production acceptance runner; merge `b86803bc95a0f05fd21fc5c4a648f18503eaecc1`.

Current behavior:
1. league switch and manual Refresh Intelligence sync canonical Sleeper State first;
2. canonical current State is authoritative and an older last-good bundle may not masquerade as current;
3. exact-State compatible Forecast / Simulation / Value artifacts may be reused;
4. missing or invalidated layers rebuild for the exact current State;
5. readiness is capability-based, not job-lifecycle-based;
6. partial Forecast, unavailable Simulation and independent current Value are represented separately;
7. no league-id/Hodor special case is present.

## Production acceptance defect #1 — silent preseason replay collapse

State-first acceptance initially reached current FSFFL State with:
- 1,675 governed raw Forecast observations;
- zero authoritative scored Forecasts;
- zero partial Forecasts;
- no Simulation blockers;
- current Value available.

Root cause: the resilient current-Forecast path correctly fell back to preserved two-source preseason raw evidence after live source health left only one healthy current source, but `build_runtime_from_preseason_baseline()` still used the old strict scorer. Players with a material missing scoring coordinate were discarded rather than represented as partial.

PR #251 — `Forecast: make preseason fallback replay truthful under partial coverage`
- accepted head: `bd02e788c616e107feef576b0627f628a73dd308`;
- merge: `672b0c2cf92db57aa2a8ba3f4ac7c537949fc698`;
- acceptance: CI, Live Forecast corrective trace, PR164 focused regression, corrective provider numerical trace, and private-beta Intrinsic diagnostics all green.

PR #251:
- replays preserved raw evidence through the modern partial-coverage scorer;
- retains partial player forecasts, scoring/family coverage and Simulation blockers;
- keeps `uncertainty_ready=False` whenever coverage blockers exist;
- bumps the replay runtime to `next2-current-runtime-v9:preseason-baseline-partial-coverage`;
- does not promote or impute any missing coordinate.

## Production acceptance defect #2 — stale Forecast cache alias

After PR #251, exact-State reuse still restored a v5 Forecast artifact created under old replay semantics. The outer Forecast artifact version had not changed, so the corrected replay did not execute.

PR #252 — `Forecast: invalidate stale replay artifacts after partial-coverage fix`
- accepted head: `955d031505af31d4aa6f77f4d978546f37ed6431`;
- merge: `262e0dcaf882f8ac1fbd3fcd9c028039e4585f5f`;
- acceptance: full CI, PR164 focused regression and Live Forecast corrective trace all green.

PR #252 bumps both the runtime and persisted Forecast evidence contract to:
`next8-live-forecast-evidence-v6:partial-replay-contract`.

That makes v5 artifacts incompatible with exact-State restore and forces a governed rebuild. Independent exact-State Value reuse remains available.

## Final production evidence

Render service: `fsffl-next-private-beta`.

Acceptance deployment:
- deploy: `dep-dari6et9fdbs739n3i80`;
- deployed main: `da0fb09c8b8876999565210455f8ecf862d78182`;
- that main is PR #252 code plus one documentation-only source-rights commit.

At 2026-09-26T01:45 UTC, the in-service State-first runner rebuilt current FSFFL State:
`f180f75af9f8d6c1af1ecb695093994e38f642a7b97ebdd9a967f7f6f1cc3a90`.

Production result:
- current canonical State: yes;
- current Value: FULL;
- raw Forecast observations: **1,675**;
- authoritative league-scored Forecasts: **0**;
- explicit partial player forecasts: **335**;
- Forecast capability: `partial_provisional`;
- Simulation: unavailable / not promoted;
- Simulation blocker: `partial_player_scoring_coordinates_present`;
- job lifecycle: completed truthfully, not false-green full capability.

The live Forecast path had only one healthy independent current source:
- Razzball accepted;
- CBS current QB response was not a valid full-season projection page;
- FFToday returned HTTP 403;
- NFL Fantasy did not contain projection content.

The resilient loader therefore used the immutable two-source preseason baseline from FFToday + Razzball, as governed.

Durable production DB evidence for the same current State:
- Forecast artifact model: `next8-live-forecast-evidence-v6:partial-replay-contract`;
- replay runtime: `next2-current-runtime-v9:preseason-baseline-partial-coverage`;
- evidence basis: `preseason_baseline`;
- raw count: 1,675;
- authoritative scored count: 0;
- partial count: 335;
- blocker: `partial_player_scoring_coordinates_present`;
- unique omitted active scoring rule: **`fum_lost`**.

This proves both implementation defects are closed. The remaining partial state is the governed consequence of missing FUMBLES_LOST Forecast evidence.

## Why this is a Management gate

Current canonical policy says:
- `FUMBLES_LOST` is a native/core conventional scoring coordinate;
- missing material active coordinates must not be silently zeroed;
- the auxiliary single-source authority study classifies FUMBLES_LOST as core/material;
- that study recommends **zero initial single-source certifications**;
- production Forecast authority is unchanged.

The preserved two-source preseason ensemble used by current FSFFL contains no FUMBLES_LOST observations. The old previously “full” FSFFL artifact also contained the same 1,675 raw observations and no FUMBLES_LOST coordinate; its full scored result was produced under older semantics that no longer satisfy the current material-coordinate contract.

Therefore implementation may not legitimately restore the old full result by:
- assuming zero fumbles lost;
- using one-source FUMBLES_LOST evidence as authoritative;
- borrowing a different horizon;
- reusing the stale old scored artifact;
- suppressing the active `fum_lost=-1` league rule.

## Management decision / external evidence required

To satisfy the existing-FSFFL “must be FULL” acceptance requirement, one of the following must occur:

1. **Evidence path:** supply/promote qualifying governed same-horizon FUMBLES_LOST evidence that satisfies the applicable independence, source-health, rights, PIT/horizon and uncertainty rules; or
2. **Authority-policy path:** Management explicitly changes the material-coordinate authority rule for FUMBLES_LOST after the appropriate Research/decision process; or
3. **Acceptance-policy path:** Management revises the requirement that this existing FSFFL league must remain FULL under the newer fail-closed FUMBLES_LOST authority contract.

No current implementation action can choose among these without changing settled model authority.

## Acceptance-run consequence

The in-service runner intentionally requires FULL FSFFL capability before continuing to Hodor → FSFFL switch and repeated manual-refresh checks. It now stops at the legitimate initial FSFFL authority gate. That is correct behavior under the current acceptance contract.

The temporary production acceptance environment gate has been disabled after evidence collection.

## Separate residuals

This gate is distinct from full K/DST authority. K/DST remains separately governed by the existing source-rights, exact-coordinate, independence, distributional and target-compatible uncertainty gates.
