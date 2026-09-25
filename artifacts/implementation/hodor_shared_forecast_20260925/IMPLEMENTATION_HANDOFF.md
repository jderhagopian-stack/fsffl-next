# FSFFL NEXT — Hodor Shared-Forecast / Partial-Coverage Corrective

Updated: 2026-09-25

## Terminal state
**DIRECTIVE COMPLETE — FORECAST / PRODUCT IMPLEMENTATION — SHARED FORECAST + PARTIAL COVERAGE**

Full K/DST authority remains a separate external-evidence blocker. This closeout does not promote it.

## Merged implementation
- PR #244 — `Forecast: restore shared Hodor population with partial coverage`
  - accepted head: `a70f0dcb7096db031b6bd5c2505b3a17272d922b`
  - merge: `edb9c0f9a1ccea4250761c63f65694d449c2d285`
- PR #245 — `Forecast: finalize generic partial-authority acceptance`
  - accepted head: `342f8c8e0ec4b0c8b1ffb5695abaf81ed98cb518`
  - merge: `7ad0d5ce4be038a2615433467227cdcfd3da85a4`
- stale PR #238 was closed unmerged after its six implementation files were verified byte-identical to current main; its exact league/state provisional K/DST hardening is already present on main.

## Final repository acceptance
PR #245 final head passed:
- CI — 1,620 tests;
- PR164 focused corrective regression;
- Live Forecast corrective trace;
- Home North Star focused validation;
- League Atlas North Star focused validation.

The generic acceptance fixture uses two unrelated synthetic Sleeper league identities with materially different scoring configurations and proves:
- canonical raw player/stat Forecast is unchanged by league identity;
- league-specific scoring is applied only downstream;
- ordinary offense can be FULL while K/DST is UNSUPPORTED;
- inactive K/DST is NOT_APPLICABLE;
- active unsupported K/DST blocks only affected downstream authority rather than the shared raw Forecast;
- no known Hodor league/team identifier controls capability.

## Corrected architecture
The production path now:
1. normalizes provider player/stat evidence independently of target-league scoring;
2. runs source-health scale checks on a fixed league-agnostic offensive fingerprint;
3. builds the authoritative raw multi-source ensemble by canonical player/stat coordinate;
4. applies target league scoring downstream;
5. emits family-level FULL / PARTIAL_PROVISIONAL / UNSUPPORTED / NOT_APPLICABLE coverage;
6. preserves explicit partial fantasy-point subtotals when supported coordinates exist but material scoring coordinates are omitted;
7. never labels a partial subtotal as canonical authoritative `FANTASY_POINTS`;
8. keeps missing evidence explicit rather than zero;
9. gates Simulation separately from Forecast population;
10. continues independent current Value work when Simulation authority is unavailable;
11. exposes current Forecast coverage and downstream blockers through the authenticated product API.

## K/DST provisional materialization
The 2026 provisional builder remains separate from canonical Forecast observations and full downstream authority.

Exact-state provisional materialization:
- requires a caller-supplied, freshly governed 2026 ROS snapshot;
- never rebinds an arbitrary persisted old snapshot to a newer state;
- persists only rights-cleared accepted subjects with qualifying independent evidence;
- binds output to exact league + league-state identity;
- research-only CBS evidence remains non-promoting;
- no production provisional artifact is fabricated when no rights-cleared qualifying current ROS evidence exists.

## Production Hodor validation
Render service: `fsffl-next-private-beta`.

### PR #244 live corrective
Deploy `dep-dare93jtqb8s73f5aoeg` ran exact merge `edb9c0f9a1ccea4250761c63f65694d449c2d285`.

Startup restored Hodor:
- league: `sleeper:1397623301961981952`;
- initial state: `3da88ba8907c51aa90d62b7119fe4b1bbc0e8a2414a38828c07cc93a7412fd52`;
- Forecast/Simulation/Value initially absent, matching the pre-corrective persisted state.

An authenticated client then:
- POSTed `/api/intelligence/jobs` successfully at 2026-09-25T21:19:21Z;
- advanced Forecast far enough to produce 330 explicit partial player-scoring outputs instead of failing `BUILDING_FORECASTS`;
- withheld Simulation with exact blockers:
  - `partial_player_scoring_coordinates_present`;
  - `separate_k_dst_forecast_authority_required`;
- served `/api/values` with HTTP 200 after the partial Forecast boundary was reached;
- refreshed canonical State to `d28de4cca9d35faeb88446449ef09984cdb57c753ef835121d70101ca56b31cb`.

This replaces the historical failure:
`LiveForecastSourceHealthFailure: authoritative live ensemble found 0 qualifying independent full-season sources under Hodor scoring`.

### Final PR #245 deployment and restart durability
Deploy `dep-daredcl9fdbs7398s55g` is live on exact merge `7ad0d5ce4be038a2615433467227cdcfd3da85a4`.

At 2026-09-25T21:26:42Z the new process restored:
- league `sleeper:1397623301961981952`;
- state `d28de4cca9d35faeb88446449ef09984cdb57c753ef835121d70101ca56b31cb`;
- `forecast=True`;
- `simulation=False`;
- `value=True`;
- `complete=False`.

That restart proves the partial-authority state is durable: valid Forecast and Value survive restart while blocked Simulation remains absent.

## Residual authority state
The shared-Forecast / partial-coverage corrective is complete.

Hodor does **not** have full league-scored Forecast/Simulation authority yet. The observed current residual is truthful:
- ordinary supported raw Forecast coordinates populate;
- 330 player-scoring outputs are partial because material active scoring coordinates remain omitted;
- K/DST remains separately unsupported for full downstream authority;
- Simulation remains unpromoted;
- full Forecast-dependent product lenses may remain unavailable where they require authoritative complete fantasy-point totals;
- current Value evidence can still exist independently.

Full K/DST authority still requires the previously governed external gates:
1. rights-cleared exact-capability live source access;
2. a second independent current ROS source for K 60+;
3. a second independent current ROS source for D/ST PA distribution and remaining rare events;
4. target-compatible full-score K/DST uncertainty promotion.

The 2026 preseason K/DST comparison remains unavailable where authentic pre-Week-1 evidence does not exist. The 2026 late-start exception remains hard-disabled for 2027+.
