# Historical evidence inventory — 2026-11-02

## Purpose and status

This is the read-only source-discovery milestone for the historical intelligence foundation. It answers what historical material is already visible in FSFFL NEXT, what it can support, and what is still missing before building a reusable historical model.

**This is an inventory, not a claim of complete data, source rights, canonical historical State, or model acceptance.** No source payload was imported, copied into this repository, or written to Supabase. The inventory is based on the repository's pinned evidence, existing operations records, and forecast source research.

## Two distinct historical evidence planes

The target requires two related but separate datasets:

1. **NFL player evidence:** point-in-time player/stat forecasts and rankings, canonical player identity, and later realized NFL outcomes. This supports the forecasting model, player history, and honest historical validation.
2. **Fantasy league evidence:** season-specific rules, rosters, transactions, picks, lineups, standings, and franchise identity at an exact cutoff. This supports historical league State, trade/decision replay, lineage, behavior, and alternate history.

A Sleeper league archive cannot substitute for historical NFL projections. Current or retrospective NFL projection files cannot establish what a fantasy league's roster or decision-maker knew at a past cutoff. Join the two only through explicit identities, timestamps, provenance, and purpose-specific contracts.

## A. Fantasy league State and transaction history

### Sources found

- The existing legacy repository `jderhagopian-stack/sleeper-league-data` contains `data/league_history.json` at commit `1179d3104cbe3330cf27e4173d61df95f2494b1a`, pinned by Git blob SHA-1 `e18c01bf25f58c5dfe3d0802f53de484ea257ca1`. It is fetched ephemerally in existing CI and deleted afterward; the raw payload is not stored in FSFFL NEXT.
- The retained archive covers one Sleeper league family for seasons 2022–2026. Existing real-source tests exercise the 2022–2026 season set. They demonstrate source availability for that one family, not general coverage of other leagues or platforms.
- The 2023 archived record has season configuration, end rosters, completed transactions, drafts, and a traded-pick ledger. Prior acceptance documented 48 completed trades and a verified source-backed October 1 example. The full reverse history also exposes an unrelated membership anomaly. This is retrospective archive evidence; it does not prove that these records or final rosters were available at the historical decision cutoff.
- Sleeper's live history adapter follows `previous_league_id` and retrieves season transactions. Existing `historical_season_lineage.py` and `historical_coverage.py` provide provider-neutral lineage and cutoff-evidence contracts. The behavioral adapter's event timestamps serve a behavioral-history use and are not, by themselves, certified effective/availability times for canonical historical State.

### Retained archive season ledger

The pinned archival CI acceptance over the same immutable source revision confirms the adjacent season chain and these season-level totals. The reconstructed roster helper separately reports membership and conditional FAAB status.

| Season | Teams | Completed events | Trades | Membership-history finding | FAAB reconstruction |
| --- | ---: | ---: | ---: | --- | --- |
| 2022 | 12 | 246 | 14 | No source-ledger issue found; startup-draft context still requires special treatment | Underflow issue; balances unknown at affected boundaries |
| 2023 | 12 | 350 | 48 | Incomplete: one completed waiver pickup is absent from the later retained roster/event history | Never independently verified as a point-in-time balance |
| 2024 | 12 | 358 | 26 | No source-ledger issue found | Underflow issue; balances unknown at affected boundaries |
| 2025 | 12 | 339 | 34 | No source-ledger issue found | Never independently verified as a point-in-time balance |
| 2026 | 12 | 107 | 22 | No source-ledger issue found in the retained slice | Never independently verified as a point-in-time balance |

The source test verifies the 2022–2026 previous_league_id chain, original per-year rules, and all five years' event totals against the pinned archive. All five recorded snapshots have 12 teams; team-count variation is synthetic-only. The 2023-to-2024 rules fingerprint changes. No row in this table certifies a contemporaneous PIT State, complete lineup/taxi/IR/standings history, or Decision-grade evidence.

**2026 is an in-progress season in this archive revision.** The helper's "archive end anchor" means the latest retained archive snapshot, not an official end-of-season roster. The same caveat applies to any later season whose archive capture is not demonstrably final.

### What it supports and what is missing

- It supports a bounded factual replay of archived roster membership and selected transaction legs, with known gaps exposed.
- Existing Supabase evidence is current-season weighted: the 2026-11-01 read-only inventory recorded 465 State history rows, all from 2026; 150 projection revisions for 2026 rest-of-season; and 180,590 market observations, all from 2026. Historical artifacts and historical sync checkpoints were both zero at that inventory. These counts do not prove historical point-in-time completeness.
- Behavioral events cover multiple seasons but are behavioral evidence, not an authoritative complete transaction ledger or proof of what an owner knew when acting.
- No second real league family/platform has passed the acquisition/reconstruction gate. The archived Sleeper fixture is one league, and synthetic variable-team-count tests do not substitute for another real source.
- Lineup, taxi, IR/reserve, standings/schedule, full pick universe, initial FAAB/balance semantics, rule changes within seasons, and original source-availability times need separate coverage assessment. Unknowns must remain explicit.
- The new draft PR #504 helper is a Sleeper-shaped retrospective roster-membership diagnostic. It is not canonical State, a cross-provider adapter, or an accepted replacement for this discovery step.

**Conclusion:** league-history evidence exists for a useful single-family research fixture. It is not yet a reusable, multi-league historical State corpus.

## B. NFL player forecasts, rankings, identity, and outcomes

### Sources found in the existing recovery matrix

The repository's `docs/forecast/modern-historical-window.md` defines 2019–2025 as the primary modern recovery window and tracks a source-by-season matrix.

- **FantasyPros raw-stat projections:** 2022 and 2023 dated artifacts are marked recovered; 2021 is a lead. Upstream rights remain unresolved. These artifacts are private-research candidates, not permission to redistribute or commercialize.
- **FFToday raw-stat projections:** season-specific 2024 and 2025 historical pages with explicit update dates are marked recovered. Terms and retained-use rights still need review.
- **NFL Fantasy:** historical pages are leads for selected seasons, including 2019, 2022, and 2025; point-in-time availability and rights remain unverified.
- **CBS, ESPN, Yahoo:** selected 2022 archive leads exist, but no broad modern season coverage is yet marked recovered.
- **Razzball:** a 2024 lead exists; historical completeness, timestamps, and terms remain unverified.
- **DynastyProcess/FantasyPros ECR:** a historical ranking archive is a ranking/consensus comparator, not raw statistical projections and not an independent projection vote.
- **nflverse/nflreadpy:** approved research path for realized outcomes and identity, subject to dataset-specific rights review.

The recovered FantasyPros and FFToday projections do not yet provide overlap across the same seasons, so the matrix does not establish a multi-source head-to-head benchmark. A source being marked RECOVERED means the dated artifact was located; it does not mean player identity, timestamp semantics, rights, or benchmark admission have passed.

### Model-ready panel status

The inventory did not identify a completed, governed row-level panel that joins:

- canonical player identity;
- source-specific raw-stat forecast and exact issue/capture/availability times;
- forecast horizon and target period;
- realized NFL outcomes from a separately governed outcome source;
- league rules/scoring only when converting raw stats to league fantasy points;
- missingness, source lineage/rights, and normalization version;
- chronological train/validation/holdout boundaries.

Existing current-season projection and market tables are not that historical panel. ECR is not a substitute for raw-stat forecasts. Later-published archives cannot be described as contemporaneously available without a defensible timestamp basis.

**Conclusion:** there are credible historical forecast acquisition leads and some dated artifacts, but not yet a sufficiently overlapping, admitted model-evaluation panel.

## C. Reuse of existing NEXT model authority

- The accepted Forecast, Value, Simulation, and Decision modules remain authoritative. Historical work should evaluate or replay them at historical cutoffs; it must not create a second valuation/scoring authority.
- The archive transaction replay and single-trade State materializer answer factual transition questions under their stated evidence gates. They do not provide historical forecasts or prove at-time trade grades.
- Prior Career / historical model research artifacts must be traced to their exact accepted code, source, training cutoff, and runtime consumer before reuse. Their existence alone does not prove a valid historical backtest panel, and missing serialized artifacts alone do not prove the methodology is lost.
- Keep actual outcome hindsight separate from ex-ante forecast/decision evidence. The same historical case may have an at-time view and an eventual-outcome view, explicitly labeled.

## Readiness and next execution order

1. **Keep this inventory read-only.** The next data step is a source-by-season recovery ledger with explicit status, source revision, observed fields/periods, timestamp basis, identity coverage, access/rights disposition, and missingness. Broaden source discovery before deep acquisition of any one provider.
2. For fantasy history, verify the Sleeper family links and per-season endpoints/coverage, then enumerate which State components each archived year actually contains. Use a secured real second-league sample only after its source and access are established; do not place private payloads in GitHub.
3. For NFL model evidence, continue the 2019–2025 source matrix, seek overlapping raw-stat projection seasons across at least three genuine sources, confirm identity and outcome joins, and resolve research-use/retention rules before admitting rows to a benchmark.
4. Build the shared row-level panel and canonical historical State from their respective evidence contracts. Preserve `effective_at`, `available_at`, actual acquisition time, source/version hashes, and season-specific rules. Report unsupported formats and incomplete history rather than coercing them.
5. Only after those data gates pass, run chronological held-out forecast/model evaluation and one fully evidenced historical league decision through existing NEXT authorities. Keep research outputs isolated from beta until separately authorized.

## Governing references

- `docs/operations/workstreams/HISTORICAL_INTELLIGENCE_FOUNDATION_20261101.md`
- `docs/forecast/historical-source-research.md`
- `docs/forecast/modern-historical-window.md`
- `docs/architecture/point-in-time-state.md`
- `docs/architecture/authority-boundaries.md`
- `docs/operations/OPERATING_PROTOCOL.md`

**Repository basis:** `jderhagopian-stack/fsffl-next`, main at inventory review `06beb75aea6f0fd46bc5efc70e4de4d4f6dbb4e3`. Inventory prepared 2026-11-02. No tests were required or run for this documentation-only discovery artifact.
