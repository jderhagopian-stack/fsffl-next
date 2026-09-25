# FSFFL NEXT — Product Roadmap

## Current critical path
1. **Forecast Research: COMPLETE.** Governed K/DST + late-connect bootstrap contract is persisted in `docs/operations/workstreams/RESEARCH.md` and `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`.
2. **Management acceptance/authorization: COMPLETE.** Bounded Forecast/Product implementation is authorized from the persisted handoff.
3. **Governed Forecast implementation: ACTIVE in PR #215:**
   - K and D/ST subject/scoring contracts;
   - active-rule completeness;
   - empirical K/DST calibration/source promotion;
   - annual snapshot v2 / evidence-preserving late-connect migration;
   - downstream compatibility.
4. Resume and complete new-league 7/7 lifecycle acceptance.
5. Physical-iPhone Market acceptance.
6. Home × Franchise redundancy/information-hierarchy audit.
7. Trade Discovery architecture review.
8. Trade Center work only after the discovery/search order of operations is settled.

## Current management gate
Research is complete and bounded implementation is authorized. PR #215 now carries the Stage 1 contracts/scoring implementation and Stage 2 non-promoting harness.

The unresolved blocker is **unpromoted empirical/source Forecast authority** for K/DST plus the late-connect preseason evidence gap. Do not interpret implemented contracts or research harnesses as production K/DST forecasts.

## Trade Discovery principle
Simulation should evaluate shortlisted trades, not perform broad discovery.

Target sequence:
`League State → needs/opportunities → candidate assets/partners → broad cheap package generation → governed filtering → bilateral plausibility → opportunity frontier → targeted simulation → deeper decision analysis`

Simulation is a microscope, not the searchlight.

## League-agnostic validation
“League-agnostic” is a target, not yet a fully proven property. Future validation must deliberately exercise configurations unlike the original FSFFL league, including K/DST where governed evidence supports them, different roster structures, and scoring differences.
