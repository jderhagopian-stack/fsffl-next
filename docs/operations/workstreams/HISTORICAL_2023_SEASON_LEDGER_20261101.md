# Historical 2023 original-source ledger reconciliation — P0 #494

**2026-11-01; NONPRODUCTION, draft, stacked on #496 -> #495 -> #493.** The purpose is a real, repeatable season-wide factual replay diagnostic, **not another State/Value/Decision model**. Latest authorized Management direction: finish reusable backend historical foundation first, independent of beta UI; use one real league as adversarial test without special-case league sizes, scoring or roster rules. Main at entry `271a8a8be8dc7611f9fc6df1a8f5f9182b5a747c` (not merged or deployed); source retains exact original 2023 league rules.

## Source and discovery

Read-only retained 2022–2026 league history: original legacy Git file `data/league_history.json` blob SHA-1 `e18c01bf25f58c5dfe3d0802f53de484ea257ca1` from `jderhagopian-stack/sleeper-league-data` pinned at commit `1179d3104cbe3330cf27e4173d61df95f2494b1a`. **Retained later, not an independently archived 2023 at-time source**. Original 2023 archive: 12 roster entries, 350 completed transactions including 48 trades, 588 player add/drop observations, 83 pick transfers, 24 FAAB transfers, 82 completed waiver bids, 21 provider-timestamp tie groups where distinct assets have no ordering overlap. No raw league file is or may be stored in NEXT. Research-only source rights; commercial provider rights not presumed.

The selected Oct 1 2023 player+pick+$10 trade remains provisionally consistent: 191 later completed events, canonical `HistoricalTradeRecord` adapter parity, 63 contract regressions + 2 pinned real-source tests passed in PR #496. This new slice **deliberately widens beyond that safe window** to all 350 events, rather than treating one good trade as a complete season.

### Real source discrepancy: 2023-07-27

Read-only independent source trace: a completed waiver acquisition is present at `2023-07-27T07:05:25.093Z`, but there is no later recorded player transfer/drop accounting for its absence from season-end `players`, `taxi` and `reserve`. Three unrelated waiver transactions share the exact completion timestamp; the affected player appears in only one, so ordering them differently does not explain the gap. No record-supported mechanism to invent an absent departure. **Expected source-wide result is `incomplete_source_history`, with one `post_event_player_missing` issue.** Missing earlier transactions are a factual limitation, not a justification for a synthesized State. The anomaly precedes the October selected trade.

## Concrete implementation

- `src/fsffl/state/retrospective_season_audit.py`: bounded, source-revision-pinned, offline-only whole-season reconciliation of player/pick movement vs archived end rosters and traded picks, completed event timestamps, source duplicate IDs, tied-asset ambiguity, season-specific rules signature, waiver bid and FAAB transfer record presence. Avoids assuming one league's teams, slots, roster sizes, scoring, rookie rounds, season chronology or provider IDs persist across years. Exposes every outstanding event issue and explicitly marks `source_provides_contemporaneous_state=false`, `historically_validated_faab_balances=false`, and `eligible_for_pit_decision_grade=false` even if a whole-season archive is internally consistent. It does **not** output canonical `LeagueState` or create new State/Value/Decision authority.
- `tests/test_retrospective_season_audit.py`: synthetic 2/8/12/16-team, scoring drift, missing waiver movement, missing pickup fee, missing end pick, duplicate transaction, independent/colliding tied events, source clock, taxi coverage, deterministic no-mutation and incomplete source.
- `tests/test_retrospective_full_2023_archive.py`: securely mounted pinned original historical file, hard assertion **one expected source-history issue** with the source timestamp and 350/48/588/83/24/82/21 counters. Skips without source and is **not accepted** until it runs non-skipped in exact-head CI.
- `scripts/audit_retrospective_sleeper_season.py`: sanitized per-year CLI: prints counters and issue-code counts **only**; exits status 2 when archive has source inconsistencies, allowing CI to assert the known issue rather than hide it.
- `.github/workflows/historical-season-2023-audit.yml`: isolated Python 3.12.10 original-archive acceptance; source fetched from already public pinned legacy Git commit, hash verified, never committed, removed from disposable runner even on failure.

## Non-negotiable distinction

This is an **independent diagnostic cross-check** of the existing retrospective replay, *not* a duplicate production reconstruction path; both new and old code remain dormant. Before promoting historical State, consolidate any duplicated source-event reverse logic into a single canonical Data/State service with independent replay-validation tests, preserve tenant isolation, original-source licensing, bounded historical workload and rules-specific identities. An internally consistent retained archive **cannot** establish historical source availability in 2023, original current-year Forecast/market evidence, ownership chronology across missing transactions or verified beginning-of-season FAAB balances. In particular, the source `waiver_budget_used` is not an inherently immutable starting FAAB balance; don't assume it resets to zero without verified league-specific semantics and recorded commissioner actions.

## Next acceptance gate

1. Exact-head GitHub **focused**, real pinned source and ordinary CI: record tests, counts and source discrepancy.
2. Find **independent factual source evidence** for July 27 (or explicitly certify a source-history coverage gap rather than make up the missing drop). Exact past State may be partially bounded after the last unresolved issue, but not whole-season authoritative.
3. Verify year-start/draft/taxi/IR roster and draft-pick ownership timeline, actual rules and periods, including the observed 2023->2024 fumbles-lost scoring change. Distinguish retained archive reconstruction from contemporaneous historical observations and Forecast/Value at-time inputs.
4. Refactor source reversal shared authority before any production publication; prove one real State-like representation with immutable evidence lineage and correct cutoffs. Keep `HistoricalTradeReport` at-time grade forbidden until Decision authority has eligible evidence and an approved historical policy.
5. No production migration, Render deploy, Supabase write, paid provider/worker or broad beta changes without explicit scoped approval and passing stable-head full-suite gate.
