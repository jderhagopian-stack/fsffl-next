# FSFFL NEXT — Current State

Updated: 2026-09-24

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

The production blocker itself is **not yet resolved**. Management has now authorized the bounded implementation described by the completed Research handoff. PR #215 is the active implementation and acceptance vehicle; Stage 1 contracts/scoring plus a non-promoting Stage 2 calibration/outcome harness are implemented there, while production K/DST provider/calibration authority remains red.

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
- the current league-scoring completeness guard has an identified `fum_lost` integrity gap that implementation must close.

## Immediate management priority
1. Complete PR #215 acceptance validation without weakening active-rule completeness or K/DST source requirements.
2. Merge only after required regression/trace checks are green.
3. Keep production K/DST authority fail-closed until separate historical calibration, source-rights/content-health, and Sleeper truth-fixture gates are satisfied.
4. Keep 2026 K/DST preseason comparison unavailable unless qualifying point-in-time raw evidence is proven; never backdate current data.
5. Resume full new-league 7/7 lifecycle acceptance only after the required Forecast authority is actually promoted.
6. Review the completed Market / Trade Discovery architecture handoff; if accepted, authorize bounded Market implementation and then repeat physical-iPhone Market acceptance.
7. Continue the Home × Franchise redundancy audit only after the Market discovery contract is accepted or Management explicitly reprioritizes it.

## Important distinction
Research completion does **not** mean the production Forecast blocker is fixed. The architecture/handoff is complete; implementation, empirical promotion, and lifecycle acceptance remain separate gates.


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

Management review of the persisted architecture is required before broad Market implementation. Market product acceptance remains open.
