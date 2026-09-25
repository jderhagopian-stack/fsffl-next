# FSFFL NEXT — Current State

Updated: 2026-09-25

## Product state
FSFFL NEXT is in private beta. The canonical authority chain remains:

`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

The North Star directive remains authoritative for product intent and presentation.

## Production / lifecycle checkpoint
Production reached the Performance management gate after PR #211. The newly selected Sleeper league is durably active; league switching and the visible Refresh Intelligence interaction are working, refresh is single-flight, and restart does not automatically launch heavy intelligence.

Full new-league 7/7 acceptance is **not complete**.

Forecast Research has now completed both the K/DST + late-connect architecture directive and the follow-on empirical/source-gate investigation.

Durable research state:
- `docs/operations/workstreams/RESEARCH.md`
- architecture: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`
- evidence-gate closeout: `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_CLOSEOUT.md`
- detailed evidence ledger: `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_LEDGER.md`

Architecture research history: PR #213 / commit `91018b39967a0775ad830a6a750a2588e7f041d0`.

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
The 2026 evidence-gate Research closeout materially updates the prior checkpoint:

- the official 2026 NFL regular season began **2026-09-09 at 8:20 p.m. ET** (`2026-09-10T00:20:00Z`);
- artifact **145** is therefore post-opener and must not be described as preseason PIT evidence;
- artifact **63** is the last recovered authentic FSFFL pre-kickoff offense Forecast artifact:
  - computed `2026-09-09T23:26:16.657633Z`;
  - FFToday + Razzball;
  - raw ensemble observations as-of `2026-09-09T23:23:53.152680Z`;
  - QB/RB/WR/TE only;
  - no K/DST and no `fumbles_lost`;
- there is still no persisted 2026 `annual_preseason_projection_snapshot`;
- a genuine pre-opener **2024 multi-provider K/DST raw corpus** was recovered from FantasySharks, ESPN and CBS, so the earlier “no historical source #2” assumption is superseded;
- authentic **2026 pre-opener K snapshots from FFToday + CBS** were recovered externally with retained timestamps and hashes;
- authentic **2026 pre-opener RotoWire-via-Sleeper D/ST component evidence** was recovered;
- a pre-opener **FantasyPros D/ST aggregate** was also recovered, but it cannot automatically count as an independent provider because its projections aggregate multiple underlying sources;
- official Sleeper documentation now resolves the ownership/meaning of K distance bands, blocked-kick misses, D/ST two-point returns, team special-teams forced fumbles/recoveries, PA/YA buckets, and subject separation;
- provider production rights remain externally gated, and the recovered K/DST evidence is not itself authorization to ingest/store/use those sources in production;
- PR #215's `fum_lost` fail-closed correction remains valid.

The historical-source gate is therefore **partially cleared**, while production Forecast authority remains **blocked** on rights-cleared, independent, rule-complete provider evidence and promoted K/DST uncertainty.

## Immediate management priority
1. Treat Forecast/Product K/DST implementation as **BLOCKED at the narrowed empirical/source authority gate**, not as unfinished Research.
2. Keep production K/DST authority fail-closed until provider rights are cleared, current rule-complete source independence is proven, and K/DST uncertainty is validly promoted.
3. For Hodor-like K scoring, require exact 50-59 vs 60+ evidence; never heuristically split 50+ data.
4. For D/ST, require a second provenance-clean component provider or licensed decomposition proving independence, and preserve game-level/distributional treatment for PA/YA buckets.
5. Reconcile the artifact-145 timing correction into any preseason migration plan: artifact 145 is post-opener; artifact 63 is the authentic pre-kickoff offense artifact.
6. Keep 2026 Hodor K/DST preseason comparison unavailable until its specific rule-complete evidence gates pass; never backdate current data.
7. Resume new-league 7/7 lifecycle acceptance only after the required Forecast authority is actually promoted.
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
