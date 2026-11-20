# Modern-model historical replay — 2026 preseason / publishing candidate

Research checkpoint: November 20, 2026
Repository: jderhagopian-stack/fsffl-next
Verified starting main: 2eaa9fb6526fad607ee12b59e8319743f8fda61e
Earlier original-vintage recovery: draft PR #575

## Management direction

The eventual FSFFL NEXT Preseason Almanac should publish results of a modern-model historical replay, preserving the original 2026 archived model only as a historical comparison. A model trained with information from after kickoff cannot masquerade as a preseason forecast.

**Cutoff**: September 9, 2026, 8:20 p.m. EDT = 2026-09-10T00:20:00Z (NFL official 2026 opening game).

Two separate lanes:
1. Modern **Simulation 2.0** on original archived preseason **Forecast**. Legitimate bounded experiment, but label as hybrid; does NOT measure the improvement from newer Forecast or provide modern Intrinsic values.
2. Complete modern historical Forecast, Simulation, 3-Year Intrinsic, Career Intrinsic and draft-pick valuation. All inputs and model-training evidence must be cutoff-admissible. This, not the partial hybrid, is the numerical target for the published almanac. Keep model/code SHA, model lineage and source receipts; no rebranding later values as preseason ones.

## Verified live database findings (read-only)

- Original pre-kickoff simulation: derived_artifact id 65, next4-live-regular-season-v4, computed 2026-09-09T23:26:17Z, 50,000 trials, 12 teams.
- Original pre-kickoff Forecast: 432 observations for 216 players, all retrieval/effective dates before kickoff.
- Player ownership: 237, future-pick ownership: 108, no conflicts against earliest full saved State.
- The earliest complete LeagueState in state_snapshot_history is **2026-09-10T12:44:36Z**, *after kickoff*, and five matchups have nonzero partial scores. It is NOT a valid preseason input despite membership corroboration. Do not change the timestamp or erase partial scores to make it appear eligible.
- Projection_snapshot and current_football_state_capture both start 2026-09-27; later inputs must not be put into a preseason model.
- Modern archived Simulation artifact id 13894 is next18-live-simulation-analytics-v19, but it is a November in-season run on another State, not a historical backcast.
- Modern weekly-volatility training is 2023–2025 (13,046 offensive player-weeks; accepted code in src/fsffl/forecast/weekly_volatility.py), so it is temporally compatible. This does NOT certify all modern Forecast, career, pick-prior or feature-selection histories.

## Additional direct-archive finding and extractable source lane

Read-only SQL compared the **pre-kickoff 2026-09-09 original Analytics team views** to the first September 10 LeagueState. All 237 player owners still match, but **two roster-slot assignments do not**: for team 8, Sam LaPorta was BENCH before kickoff and TE the following day, while Travis Kelce was TE before kickoff and BENCH the following day. Therefore postgame State is incorrect even for some starting/bench placement. Use original preserved 2026-09-09 roster slots as the authoritative historical membership/placement source, not the 9/10 snapshot.

Pre-kickoff archive id65 contains 237 rostered players, all with source-era roster slots, and 108 future-pick ownership rows. 216 distinct rostered players have exact *season fantasy_points* Forecast observations, each accompanied by a fantasy_regular_season horizon observation (432 total). The other 21 players have **no archived Forecast observation**; never invent 0 projections. 29 players are IR/TAXI. The archive does not carry NFL club identities or complete source-era injury/league-rule provenance, so it is a partial historical State input only.

Research source adapter scripts/research_preseason_archive_bridge.py extracts original roster slots, pick ownership and surviving season Forecast observations with source clocks and fails closed on conflicting IDs/late evidence. Synthetic contract tests in tests/test_research_preseason_archive_bridge.py. Original tenant payload stays private and is not included in this repo.

## Prototype implementation

- scripts/research_modern_preseason_replay.py: pure read-only historical admission checks for canonical State, original 2026 season Forecast evidence, sourced/trained parameter history, bye and roster data, and zero post-kickoff fantasy points. When evidence passes, --run invokes the existing FSFFL NEXT product Simulation 2.0 (build_live_simulation_analytics), with 50,000 NumPy PCG64 trials, not a second simulation engine.
- tests/test_research_modern_preseason_replay.py: 14 synthetic admission tests, including wrong vintage, leaked scoring, missing model receipts, post-cutoff training, missing byes, duplicate/late forecasts.
- .github/workflows/research-modern-preseason-replay.yml: standalone focused research CI. No private data or credentials needed.

**Current status**: Research-only implementation and provenance gates prepared. No complete 2026-09-09 State pack has been validated by this new runner. No modern 2026 simulation has been executed in this workstream. No modern championship probabilities are authorized for publication. The runner always returns publication_ready=false until modern Forecast and both Intrinsic horizons have independent historical validation.

## Next evidence and execution gates

1. Reconstruct/independently attest the **pre-kickoff** canonical State (league rules, roster placements, player status, picks, schedule, NFL byes, player availability). Use the already accepted historical replay code; later State can corroborate only ownership, not source timing. Keep explicit blockers per fact group.
2. Securely load archived September 9 Fantasy Points Forecast from derived_artifact #65 / matching #63 into an offline private runner. Prove source effective/retrieval clocks; never commit raw tenant data.
3. Execute and record the modern Simulator against this State and old Forecast as a **hybrid research result**, not a full modern-model publication.
4. For complete modern Forecast: audit model parameters/training cutoffs (<= historical cutoff), re-materialize using no 2026 in-season results. Reuse governed first-party fumbles completion, status and uncertainty policies as PIT permits; otherwise explicit failure. No defaulting missing estimates to zero.
5. Recompute modern 3-Year and Career from the same admissible historic Forecast inputs, honoring existing authority; include draft pick Intrinsic only when its independent research is promoted and PIT-valid. Do not use the present 2026-11 model output as a source row.
6. Run same-State original-versus-modern validation with code SHA, source receipts, model parameters/versions, coverage, and real heldout calibration evidence.
7. Build a compact versioned Reports & History publishing manifest. Preserve original archived prediction for The Receipts; display modern backcast as such and freeze the edition. Presentation never invents numbers or overwrites model outputs.
8. Focused tests, private exact-source decode, exact-head CI/Stable where applicable, explicit publication acceptance, and no extra infrastructure or production writes.

No Render deployment, billing changes, new provider account, secret export, new data tables, or direct live model changes are authorized or claimed.