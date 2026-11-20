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
## Additional pregame raw-Forecast source confirmed (read-only SQL)

The original `current_forecast_evidence` artifact **id 63** preserves **1,680** unique season raw-metric observations for **336** players, with two independent constituent projection sources (FFToday and Razzball), no post-kickoff availability/retrieval/effective timestamps, and accepted original coverage minimum 2. The metrics are completions/interceptions? Specifically verified retained metrics: interceptions, pass_td, pass_yards, rush_td, rush_yards, receptions, rec_td and rec_yards. These inputs are upstream of fantasy-point scoring, and are stronger candidates for governed newer Forecast re-scoring than simply relabeling the old Fantasy Points outputs. No future data or new source was supplied.

Research adapter `extract_preseason_raw_forecast_evidence()` in `scripts/research_preseason_archive_bridge.py` validates the untouched source cutoff and emits a **raw vintage**, expressly **not** an approved modern Forecast. Five targeted synthetic regressions extend its contract.

Important negative evidence: every one of the first later State snapshot's **809** player-status rows, **32** NFL bye rows and **84** matchup rows has recorded source effective/retrieval time **September 10 12:44 UTC**, after kickoff. Those later receipts cannot make a historic Sept 9 football-state input by editing timestamps. Separate pre-kickoff published schedule and player-status evidence is required.

The current `FirstPartyFumblesLostSupplement` contract explicitly declares `preseason_eligible=false` and `historical_pit_eligible=false`, with a completed-Week-2-or-later requirement. Do not run this present in-season-only FUMBLES_LOST policy as if it were preseason-authorized. A separately governed PIT source/first-party preseason model or an explicit coverage blocker is required for full current Forecast.

**Checks**: Exact-head focused research workflow on commit `a75f11f8331584d422a325f53d90d599a95765c7` completed **29 synthetic tests passed**, Python compile passed (GitHub Actions workflow run `44736261180`). This is not a full private production payload decode, modern Forecast run or 50k modern simulated season.

## Direct source-coverage reconciliation

Further read-only join of archived Analytics #65 and raw Forecast #63: among **237 rostered players**, **216** had a direct preseason full-season fantasy-point Forecast, and **21** lacked that final Forecast. Of those 21, **12** were IR/TAXI and **9** were on active roster slots. None of those **nine active-roster missing players** had a corresponding pre-cutoff raw-metric Forecast in artifact #63 either. The archival simulation's original "nine position-floor forecasts" warning is therefore independently consistent with this direct-vintage coverage. Modern re-scoring cannot recover missing source projections by processing existing raw rows alone. A governed, PIT-compatible prior/fallback must be explicitly admitted (or each unscored subject must remain a named coverage failure). Do not silently impute zero or introduce future provider rows.

## 2026-11-20: executed September 4 pinned-source 50k hybrid pilot

A new research-only offline harness (`scripts/research_frozen_2026_hybrid_simulation.py`) uses **10 immutable Git-blob-verified public files** from historical FSFFL repo commit `72c926cdcf9450d1ba1dcb53f67d698851b54cfb` dated **September 4, before kickoff**. It builds the canonical `LeagueState` using accepted `SleeperSnapshotNormalizer`, applies explicit dated fact corrections, attaches **231 historical legacy preseason player forecasts**, then calls existing `build_live_simulation_analytics` on its accepted NumPy/PCG64 kernel with seed 20260905 and **50,000 trials**. Research output only, no runtime backend state mutation, no private raw data in CI, no Render/Supabase changes.

**Verified input**: 12 franchises, 243 rostered players, 108 future-pick ownerships, 84 fantasy matchups, all 32 NFL byes, no completed fantasy weeks, 231 direct player forecasts; **12 rostered lacked direct forecasts**, receiving the existing governed same-position conservative fallback if eligible. These Sep 4 counts are not the same as Sep 9 (237 rostered, 9 active fallback).

**Important new temporal cross-check**: September 4 public roster versus September 9 archived original FSFFL NEXT showed 24 distinct player membership or ownership discrepancies. These vintages must never be represented as matching. Also September 4 source NFL club field for `sleeper:player:12504` Kaleb Johnson was PIT, though the Packers publicly announced his acquisition on **August 30, 2026**. The research adapter records the single explicit dated original club announcement at `https://www.packers.com/news/packers-announce-roster-moves-aug-30-2026` and applies PIT→GB in canonical Player and PlayerState, retaining a separate retrospective-recovery receipt. This is not permission to import unrelated post-cutoff player status facts.

**Executed outcome**: GitHub Actions run `44744550445` completed 50k simulation. Corrected rerun `44745834747` / job `136325491410` also completed 50k and repeated a second 50k pass for exact same-simulation deterministic equality, **all passed**. Correcting the club field did not change team standings/title percentages at the displayed precision. In a prior attempt, GitHub transiently returned `503 Backend.max_conn reached` during a repeated fetch (not a modeling failure); the new harness caches source bytes only in CI job scratch space and verifies git blob hash on every reuse, with bounded retry. Synthetic tests now cover cache integrity.

**Actual current Simulation 2.0 hybrid ranking** (Sept4 vintage; 50k):
- T8 Bodini: 9.79 wins, 93.6% playoffs, 26.9% title
- T2 Chef Niners: 9.04, 87.4%, 17.9%
- T11 BING BONG DRIGSY: 9.03, 87.0%, 22.7%
- T9 Hurts So Good: 8.81, 82.6%, 11.1%
- T7 MochaSmevs: 8.11, 68.4%, 7.7%
- T12 King B: 7.58, 55.3%, 4.8%
- T10 Shish Kebab Boys: 7.23, 50.1%, 4.8%
- T5 Ball Knower: 6.73, 34.3%, 2.1%
- T3 STINKS: 6.41, 27.5%, 1.6%
- T6 Trash Incessant Talkers: 5.77, 13.5%, 0.3%
- T4 The Associate: 2.81, 0.2%, 0.0%
- T1 HUNGRY DAWGS: 2.69, 0.2%, 0.0%

**Research label**: `modern_simulation_on_legacy_2026_preseason_forecasts`, NOT "complete modern-model historical replay" and NOT a numerical final almanac release. Legacy projection source discloses **PERSONAL_RESEARCH** rights and noncommercial default; commercial publication/distribution needs separate source rights assessment. Do not promote preliminary probabilities or claim improvement solely from comparing September 3 Legacy Simulation 1.0 to September 4 NEXT Simulation 2.0, because the input vintage and simulation internals differ.

**Next hard gate**: materially exact September 9 State with dated changes, use original #63 raw forecast evidence (336 players) for current Forecast re-scoring where supported, and execute PIT-approved missing fumbles model/fallback; then separately rebuild 3-Year and Career Intrinsic. Frozen historical stage is retained as a useful benchmarking pilot and Report Studio editorial insert; a full modern-model 2026 almanac is not yet authorized.


## 2026-11-20 Management correction — Travis Hunter: preserved on BING BONG DRIGSY

**Management confirmed that Travis Hunter has continuously been on BING BONG DRIGSY.** Historical Sleeper source `data/rosters.json`, pinned commit `72c926cdcf9450d1ba1dcb53f67d698851b54cfb`, independently corroborates roster 11, player `12530`, on BENCH, and complete pre-cutoff behavior-event history does not show a corresponding drop or transfer. **Do not remove Hunter** or invent a transaction.

Archived Analytics #65 omits him entirely, and the earliest persisted canonical State snapshot likewise lacks him. Those rows are **incomplete coverage**, not a complete roster membership authority. The reconstruction now deliberately preserves **238** players with Hunter assigned to team 11; the historical Analytics hash represents only the **237** other subjects, validated as a strict subset. All **108** retained pick owners remain reconciled. The original 9/9 Analytics row count and subsequent source corroboration cannot be presented as a complete 238-player source.

Potential defect to investigate in the normalizer: `src/fsffl/providers/sleeper.py` resolves player identity from the single `raw.position` field and drops entries where `_position_map.get(raw_position)` is None, despite Sleeper supporting `fantasy_positions`. The pregame older player catalog lists Hunter primary WR and fantasy positions DB/WR; a later provider primary position of DB *could* explain exclusion. This is a hypothesis, **not verified cause**, until raw 9/9 player-catalog evidence is recovered. Add a real regression before changing production normalization.

No published almanac, model replay or intrinsic calculation may treat an absent analytics subject as a confirmed roster departure.
