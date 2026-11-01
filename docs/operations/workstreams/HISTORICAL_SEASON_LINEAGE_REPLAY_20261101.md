# Historical Foundation #494 — Source-backed league-season lineage and factual trade witness

Status: **NONPRODUCTION IMPLEMENTATION — STACKED DRAFT PR; NO LIVE DATA MIGRATION OR PROMOTION**. Parent: PR #493 (historical PIT admission and truthful evidence inventory), issue #494. Canonical authorities: `docs/charter.md`, `docs/NORTH_STAR_PRODUCT_DIRECTIVE.md`, `docs/operations/OPERATING_PROTOCOL.md`, `docs/architecture/authority-boundaries.md`, `docs/architecture/point-in-time-state.md`, and prior historical-grader/rights research. User has selected historical-backend-first with full league agnosticism. The existing private beta, accepted analytical models and worker candidate #492 are not being changed.

## Evidence and real-world blocker

On November 1, Supabase read-only inspection shows historical **Behavioral events** for 2022–2026 but only **2026** canonical `state_snapshot_history` State snapshots, ROS projection revisions and market observation dates. The historical report/sync-checkpoint tables contain zero records. Completed Behavioral scans do **not** prove a recoverable historical pre-trade roster, pick ownership, scoring/roster rule configuration, original market forecast, or verified trade ledger. No canonical 2023 State or real historical trade acceptance is claimed.

The predecessor `jderhagopian-stack/sleeper-league-data` has an `fsffl_historical_state_provider.py` method to reverse a completed transaction ledger from a season-end snapshot. Its algorithm is informative **only as a research candidate**. It reconstructs a historical snapshot from a current/season-end record, and its specialized Alternate History source archive (`data/alternate_history/source_history/sleeper_history.json`) was **not present** in the inspected repository tree. **However, a different retained source, `data/league_history.json`, WAS discovered and inspected via the GitHub blob API; it contains full season-level records for 2022–2026.** Its latest visible commit is dated 2026-08-30, which does not establish 2022–2025 original at-time availability. The old reconstruction algorithm remains a research candidate, not original source-time certification. First pilot must find/acquire actual historical original season rules, roster/pick/FAAB snapshots, transaction logs and provenance. Verified post-hoc factual reconstruction and at-time Decision eligibility are separate standards.

## Newly identified actual league-season source (read-only, retained in original repo)

**Discovery revised during implementation:** Original FSFFL repository `jderhagopian-stack/sleeper-league-data`, `data/league_history.json`, immutable Git blob `e18c01bf25f58c5dfe3d0802f53de484ea257ca1` (1,799,889 source bytes) contains five source-backed Sleeper season records for 2022, 2023, 2024, 2025, 2026. Each record includes per-season raw `league` settings, scoring, roster positions, 12 roster entries, users, a draft, traded picks and the actual season transaction list. Provider `previous_league_id` pointers were confirmed consistent in every adjacent pair (2022→23→24→25→26). **No raw IDs, users, rosters, or historical payloads are moved to NEXT or published by this PR.** Counts below are aggregate inspection only.

| Season | Provider roster rows | Raw transaction rows | Completed trade rows |
|---|---:|---:|---:|
| 2022 | 12 | 306 | 14 |
| 2023 | 12 | 420 | 48 |
| 2024 | 12 | 456 | 26 |
| 2025 | 12 | 434 | 34 |
| 2026 | 12 | 113 | 22 |

**Real observed historical rule drift:** raw 2022→2023 settings differ in reserve slots, waiver settings and deadline; 2023→2024 changes include `reserve_slots` and the scoring coordinate `fum_lost` as well as other settings; later years differ in configurable waivers and other settings. Raw lineup labels include `SUPER_FLEX` and `BN`, which are verified Sleeper aliases for canonical `SUPERFLEX` and `BENCH`; preserve their original spellings, and do not treat unfamiliar IDP codes as conventional offense. Real historical league count happened to remain 12; synthetic tests with 2/8/10/14/16 ensure the core contract does not hard-code 12. **This evidence strengthens historical facts and linked-season source retrieval but does not prove older market/ROS projections existed at the relevant date or that the archived source faithfully includes every provider event.** Its current blob was refreshed in 2026; verify historic/source timestamps separately before PIT Decision grading.

The official Sleeper API documentation (https://docs.sleeper.com/) states that the public read-only API is free for **non-commercial** use and requires contacting Sleeper about commercial licensing. This repo-first beta history study is research only. Do not assume a future commercial NEXT can ingest or redistribute Sleeper data under current terms; obtain a separately documented permissible commercial-use basis before public productization. Use no new provider calls for this PR.

## This PR implements

1. **Season source inventory** (`src/fsffl/state/historical_season_lineage.py`): immutable provider-neutral season identity, independent per-year provider league IDs, declared team count and explicit season-scoped roster/team crosswalk. No automatic franchise or owner continuity is inferred from names or reused roster IDs. Explicit verified parent provider IDs are required to link seasons. Conflicts, duplicate identities, forks, unsupported slot codes (e.g., IDP), partial roster mapping and missing availability proof are not converted to passing evidence. Optional source SHA-256 pointer supports a later private byte-integrity gate; missing hash is an inventory, never model admission.
2. **Evidence-kind support**: original settings and roster snapshot receipts join the existing exact-cutoff evidence schema; no new forecast authority or database write. `effective_at` remains different from source `available_at`, which must have a documented provider/archive proof to be PIT-eligible.
3. **Factual trade witness** (`src/fsffl/state/historical_trade_transition.py`): Given original provenance-backed canonical *before/after* States and an already normalized `HistoricalTradeRecord`, verify player movement, pick ownership, FAAB balances and absence of extra movements for an isolated two-team event. Failure labels distinguish wrong transfers, other intervening moves, and unsupported three-or-more-team destination ambiguity. This operation is retrospective **fact validation only**, not a 2023 at-the-time valuation, grade, or counterfactual. Does not mutate input, fetch provider data or publish.
4. **Deterministic synthetic tests**: league sizes 2/8/10/12/14/16, different season IDs, different rule identities, Superflex/K/DST, explicit IDP unsupported status, cross-tenant or cross-league rejection, reused roster IDs, linked/unlinked years, 8/12/16-team player/pick/FAAB trade witnesses, missing transfers, auxiliary waiver moves and 3+ party failure. Existing historical State/Trade tests remain in the focused gate.

## Known limitations: explicit, not silent

- Still no live 2022–2025 canonical State, source rights and complete historical provider archive. All positive trade witness tests use **synthetic**, not original FSFFL records.
- The original `HistoricalTradeRecord` identifies *senders* only. With three or more parties, asset destinations are not uniquely encoded. A later version needs explicit source-backed transfer edges before 3+ party historical verification. No bilateral simplification of multi-party trades.
- A receipt's verified time/identity does not independently prove the underlying raw bytes; the ingestion/storage boundary must verify original source hashes, timestamp semantics, rights, and tenant isolation. This code is not a trusted source-acquisition layer.
- Unsupported positions (IDP etc.) are surfaced but cannot currently be modeled by the downstream Forecast/Value/Simulation authorities. A source mapping is not proof that all scoring statistics are supported. Missing historical scoring/rule changes must be recorded as unavailable, not inherited from 2026.
- No database schema changes or extra connections; persistent data must use the existing bounded pooled PostgreSQL path if approved in a later slice. No provider requests, production refresh, paid compute or raw private data in GitHub.
- The historical State snapshot/pick/FAAB evidence must correspond to the **actual** trade date, not a later retrospective estimate labeled original. At-time Decision requires separate eligible historical Forecast/Value/uncertainty and source licensing. The retrospective witness may be true without that Decision evidence.
- The witness is intentionally strict: if multiple transactions occurred between two snapshots, record `AMBIGUOUS`, then reconstruct at an event boundary; don't smuggle intervening action into the trade.

## Next small slice and acceptance

1. Read-only identify the source-backed per-year league family lineage from an original provider's previous-league ID chain (or a separately documented archive), verifying all year-specific settings and reliable roster crosswalk. No fragile name matching.
2. Audit historical transaction counts per year/league and direct original source archive presence/rights; choose one 2023 trade *only if* pre/post roster/pick/FAAB original evidence can be acquired or a carefully governed retrospective reconstruction is explicitly labeled as such.
3. Implement one provider adapter for original season data behind the existing canonical Data → State authority. Produce a **private** 2023 exact pre/post canonical State and reconcile its transaction with this factual witness. Do not upload source or user data. If originals unavailable, report a bounded blocker with an evidence coverage matrix; proceed with rights-safe other-league fixture testing rather than inventing history.
4. Validate historical source effective times, scoring/roster changes, transaction coverage, pick ownership and original-to-canonical lineage across ≥2 different league setups and ≥2 seasons; sample output and numerical results only after grounded source evidence exists.
5. Only after prior step passes, determine value of at-time vs hindsight Decision evaluation, historical pick coordinate and evaluation, and materialized long-lived immutable history using the accepted persistence ownership contract. No UI expansion yet.

## Engineering discipline

Stacked draft PR from PR #493, isolated from #492 and production. Focused test + Python 3.12.10 CI now; stable-head full suite only when ready to merge and original parent PR has been accepted. No premature merge/deploy. Record exact CI head and discrepancy. No alteration to accepted 3-Year/Career or calibrated model math.
