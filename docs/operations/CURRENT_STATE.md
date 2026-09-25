# FSFFL NEXT — Current State

Updated: 2026-09-25

## Product state
FSFFL NEXT is in private beta. The canonical authority chain remains:

`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

The North Star directive remains authoritative for product intent and presentation.

## Production / lifecycle checkpoint
Production reached the Performance management gate after PR #211. The newly selected Sleeper league is durably active; league switching and the visible Refresh Intelligence interaction are working, refresh is single-flight, and restart does not automatically launch heavy intelligence.

Full new-league 7/7 acceptance is **not complete**.

The prior research dependency is now resolved: Forecast Research completed the K/DST + late-connect bootstrap directive and persisted the governed contract in:
- `docs/operations/workstreams/RESEARCH.md`
- `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

Research history: PR #213 / commit `91018b39967a0775ad830a6a750a2588e7f041d0`.

The production blocker itself is **not yet resolved**. Bounded Forecast implementation PR #215 is now merged to canonical main at `407c1bf85e5dc75f92b9906719f82bcd11d97c31`. Stage 1 subject/scoring integrity and the non-promoting Stage 2 outcome/calibration harness are implemented and regression-clean. Production K/DST provider/calibration authority remains red at the empirical/source evidence gate.

## Completed research determination
The accepted research contract establishes:
- K is a distinct Forecast family but remains an individual-player subject.
- D/ST is a canonical NFL team-season unit rather than an ordinary player.
- provider eligibility and source independence are rule/metric specific;
- D/ST points/yards-allowed buckets require distributional game-level treatment rather than season-average substitution;
- K and D/ST require separate empirical uncertainty calibration;
- annual preseason Forecast authority should remain league-agnostic raw evidence;
- late-connected leagues may use an existing annual snapshot or evidence-preserving migration of genuine retained point-in-time raw evidence;
- absent qualifying preseason evidence, preseason comparison must fail closed while current-forward Forecast may operate independently if its own authority gates pass;
- existing offensive-player Forecast authority and two-source governance must not be weakened.

## Production evidence relevant to the next gate
Read-only research inspection established:
- there is no persisted 2026 `annual_preseason_projection_snapshot`;
- legacy baseline artifact 145 is authentic 2026 offensive PIT evidence from FFToday + Razzball with 1,675 raw ensemble observations;
- that artifact has no `fumbles_lost` observations and therefore is not universally replayable under arbitrary target scoring;
- no qualifying persisted two-source 2026 preseason K/DST raw package is proven;
- PR #215 closed the `fum_lost` integrity gap: active missing evidence now withholds authoritative fantasy points and CBS no longer manufactures a missing FL value as zero;
- a post-merge evidence check did not recover a qualifying independent historical K/DST source #2; dated Razzball material points to mutable current endpoints and CBS historical-looking paths are not sufficient PIT provenance;
- candidate Razzball/CBS/Sleeper production use remains rights/licensing gated under the currently published terms/documentation.

## Immediate management priority
1. Treat Forecast/Product K/DST implementation as **BLOCKED at the empirical/source evidence gate**, not as an unfinished PR.
2. Keep production K/DST authority fail-closed until a second independent historical PIT corpus, production source rights/content health, and the remaining Sleeper truth-fixture requirements are satisfied.
3. Keep 2026 K/DST preseason comparison unavailable unless qualifying point-in-time raw evidence is proven; never backdate current data.
4. Resume new-league 7/7 lifecycle acceptance only after the required Forecast authority is actually promoted.
5. Merge/deploy the implementation-accepted Market PR #220, then repeat physical-iPhone/Safari Market acceptance.
6. Keep Market acceptance separate from the blocked Forecast/K/DST empirical/source evidence gate; do not weaken either authority to unblock the other.
7. Continue Home × Franchise redundancy audit only after Market physical acceptance or explicit Management reprioritization.

## Important distinction
Research and bounded code implementation are complete for the currently authorized evidence-independent scope. Production Forecast support is still blocked on empirical/source evidence promotion and subsequent downstream/lifecycle acceptance. See `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`.


## Market discovery architecture checkpoint — 2026-09-24
The Market / Trade Discovery Architecture Review is complete and has stopped at **MANAGEMENT GATE**.

Persisted handoff:
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

Key determination:
- current broad Search is package-row-first;
- it emits nearest one-, two-, and three-asset Cardinal matches per opposing player target;
- exact-only deduplication and multi-lane package ordering allow repeated target neighborhoods before opportunity-family clustering;
- the quick Market payload contains zero bilateral Decision enrichment and the full workspace normally evaluates only one row;
- For You then fills remaining “high-signal” slots from raw Search order;
- Decision already owns the package-economics, cut-cost, bilateral consequence, and negotiation-feasibility primitives needed for a bounded pre-Simulation screen;
- exact changed-state Simulation does not need to become broad discovery and remains downstream of a selected transaction;
- global 7/7 proves the core State/Forecast/current-Simulation/Value lifecycle, not the separately lazy all-player Intrinsic/Market consumer contract, which explains the current Player Board / Free Agents contradiction.

Management subsequently accepted the architecture and authorized bounded implementation. PR #220 now satisfies implementation-level acceptance; Market product acceptance remains open only for the required merged/deployed physical-iPhone/Safari validation.


## Market implementation checkpoint — 2026-09-25
The Management-authorized Market / Trade Discovery implementation is complete at the implementation level.

Evidence:
- PR #220;
- `artifacts/implementation/market_discovery_north_star_20260925/IMPLEMENTATION_HANDOFF.md`;
- final code head `97ff2a4e59d065b38a6eb751c3ed3a330feee56e` passed full CI, Home, Franchise, League Atlas, PR164 corrective regression, and live Forecast corrective trace.

The implementation preserves the accepted authority chain and zero broad changed-state Simulation. The next gate is merged/deployed physical-iPhone/Safari product acceptance, not additional speculative redesign.
