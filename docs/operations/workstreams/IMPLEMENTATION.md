# FSFFL NEXT — Forecast / Product Implementation

Updated: 2026-09-25

## State
**BLOCKED — BOUNDED 2026 LATE-START IMPLEMENTATION COMPLETE; PRODUCTION AUTHORITY AWAITS EXTERNAL EVIDENCE / RIGHTS.**

Management accepted the completed K/DST + late-connect Research contract and authorized its bounded implementation. The base architecture remains authoritative:
- `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

Management's current implementation authority is:
- `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`
- `artifacts/implementation/k_dst_late_start_20260925/IMPLEMENTATION_HANDOFF.md`

Implementation PR **#215** is merged on canonical main at `407c1bf85e5dc75f92b9906719f82bcd11d97c31`.

Management-authorized late-start implementation PR **#233** is merged on canonical main at `79c1f0c0aa094e4b1e3f6aa41eacd08c6bf1d6e8`. Its reconciled head `1e9eb293c7029b0953c3ecec8353b8c2638ea35e` passed full CI, PR164 focused corrective regression, Live Forecast corrective trace, and Corrective live provider numerical trace before merge.

## Implemented in the active PR
### Stage 1 — contracts and scoring
- canonical NFL team identity/aliases shared across State and Forecast;
- K remains an individual-player Forecast family;
- D/ST has a canonical NFL team-season Forecast subject and player-shaped D/ST observations are rejected;
- K and D/ST raw metric contracts are explicit;
- rule-level source evidence carries an independence-group identity;
- K exact vs exact-derived coverage is explicit, including no 50+ heuristic split into 50–59 / 60+;
- D/ST linear event scoring is distinct from per-game distributional points/yards-allowed bucket scoring;
- team special-teams and player special-teams semantics remain separate;
- active missing `fum_lost` evidence fails closed rather than silently contributing zero;
- CBS no longer manufactures a zero fumble-loss projection when the provider column is absent;
- Sleeper rostered D/ST assets retain canonical team identity for the roster→Forecast team-unit boundary;
- unrostered Sleeper player enrichment includes K but does not reinterpret D/ST as a player Forecast subject.

### Stage 2 — non-promoting research harness
- deterministic nflverse-style K realized-outcome reconstruction;
- conservative directly observable D/ST realized-event reconstruction;
- explicit missing kick-distance completeness defects rather than guessed distance bands;
- non-promoting season-error fitting gated on at least two independent sources;
- weekly volatility fitting uses realized game scores rather than season-total / 17 shortcuts.

## Authority deliberately not promoted
The PR does **not** create or claim:
- live K/D/ST provider authority;
- a K or D/ST production uncertainty coefficient;
- a qualifying 2026 K/DST preseason baseline;
- current/post-opener data relabeled as preseason;
- annual-snapshot-v2 migration acceptance;
- K/DST Value, Simulation, Decision, Search, or Presentation truth;
- any weakening of the existing two-independent-source requirement.

## Acceptance validation
The first PR run correctly exposed historical synthetic fixtures that had relied on an implicit missing-`fum_lost` zero. Those fixtures were repaired by supplying explicit synthetic zero observations only where the fixture itself owns that evidence. Runtime/provider evidence remains fail-closed.

After reconciliation with concurrent Market operating-state changes, the final PR #215 head passed full CI, focused corrective regression, private-beta Intrinsic diagnostics, live Forecast corrective trace, and the governed live-provider quarantine trace, then merged to main.

Post-merge Stage 2 evidence recovery was also attempted. The result is persisted in `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`: no qualifying second historical independent K/DST PIT corpus was recovered, and candidate production sources remain rights/licensing gated.

## Remaining evidence gates after PR #233
The bounded implementation is complete. Production K/DST authority remains fail-closed until:
1. authorized live API/source access and deployable rights are available for an exact-capability provider path;
2. a second independent current ROS source proves the Hodor-specific K 60+ coordinate;
3. a second independent current ROS source proves D/ST remaining-game PA distribution plus the remaining rare-event coordinates;
4. target-compatible full-score K and D/ST uncertainty is empirically promoted under an exact scoring fingerprint;
5. only after Forecast authority is genuinely green, the new-league lifecycle is re-run for downstream acceptance.

The 2026 preseason comparison remains explicitly unavailable where authentic pre-Week-1 K/DST evidence does not exist. Missing preseason evidence is no longer a current-forward blocker.

These are external evidence/rights dependencies. They may not be bypassed with offense coefficients, one-source estimates, synthetic production values, zero uncertainty, average-based D/ST bucket reconstruction, or backdated current data.

## 2026 late-start exception implementation
Management superseded the prior blanket implementation stop with a bounded one-season-only 2026 current-date ROS authorization. PR #233 completed that evidence-independent implementation while preserving the remaining rights/exact-coordinate/uncertainty gates.

The merged implementation includes the dedicated non-preseason artifact, hard 2026 boundary, schedule-aware row quarantine, rights-aware independent-source coverage, K/DST ROS normalization, exact K algebraic transforms, explicit calibration fingerprints, deterministic replay/holdout diagnostics, and no-zero-uncertainty authority assessment.

The late-start artifact is not preseason authority. It is hard-disabled for 2027+.

## Next authorized action
No further production-authority implementation is possible from presently available governed evidence. Resume only when authorized API/source access or a newly supplied independent exact-capability source can materially clear a remaining gate. Do not substitute heuristics.

**BLOCKED — FORECAST / PRODUCT IMPLEMENTATION — EXTERNAL SOURCE RIGHTS + SECOND-SOURCE EXACT COORDINATES + TARGET-COMPATIBLE UNCERTAINTY**
