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

The production blocker itself is **not yet resolved**. The newly connected league still requires implementation and evidence promotion for K/DST Forecast authority, governed late-connect bootstrap behavior, and downstream compatibility. No implementation is authorized by the completed Research directive.

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
1. Review and accept the completed Forecast Research contract.
2. If accepted, authorize a bounded Forecast/Product implementation directive from the persisted handoff.
3. Keep implementation fail-closed where historical K/DST calibration/source evidence is not yet promoted.
4. Resume full new-league 7/7 lifecycle acceptance only after governed Forecast implementation is complete.
5. Then continue Market physical-iPhone acceptance, Home × Franchise redundancy audit, and Trade Discovery architecture review.

## Important distinction
Research completion does **not** mean the production Forecast blocker is fixed. The architecture/handoff is complete; implementation, empirical promotion, and lifecycle acceptance remain separate gates.
