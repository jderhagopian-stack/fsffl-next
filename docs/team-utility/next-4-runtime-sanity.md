# NEXT-4 Runtime League Sanity Harness

This runtime harness exists to execute realistic NEXT-4 validation without storing a user's live league data in the repository.

## Charter boundary

The harness is orchestration, not model authority. It may sequence Data -> State -> Forecast -> Team Utility / Simulation. It may not invent forecasts, schedules, competitive-state thresholds, value mappings, owner intent, trade recommendations, analytics, or presentation logic.

## Runtime flow

1. A league identifier is supplied at execution time.
2. `SleeperLiveSource` acquires the current provider payload at the Data boundary.
3. `SleeperSnapshotNormalizer` converts the provider payload into canonical NEXT-1 `LeagueState`.
4. The caller supplies admissible NEXT-2 `ForecastObservation` inputs.
5. The caller supplies an explicit modeled schedule and playoff-team count.
6. The caller supplies an explicit governed `CompetitiveStatePolicy`.
7. Optional NEXT-3 `FranchiseAssetPortfolio` evidence may be supplied by team.
8. `run_next4_league_sanity` builds optimized lineups, team scoring distributions, competitive simulation outcomes, roster resilience, and non-collapsing team utility vectors for every team.
9. The result is structured diagnostic data. Reporting and visualization remain NEXT-7 responsibilities.

## No league data in git

The repository contains only the acquisition, normalization, orchestration, models, tests, and validation logic. League identifiers and fetched provider payloads are runtime inputs and are not committed by this harness.

If reproducible point-in-time snapshots are retained in the future, they belong in governed private/runtime storage under the NEXT data architecture, not in the public source repository.

## CLI

`scripts/run_next4_league_sanity.py` accepts:

- `--league-id`
- `--forecasts`
- `--schedule`
- `--competitive-state-policy`
- `--playoff-teams`
- optional `--asset-portfolios`
- optional `--horizon`
- optional `--simulations` (default 50,000)
- optional `--seed`

The CLI emits the structured `Next4LeagueSanityResult` as JSON.

## Fail-closed behavior

The harness deliberately does not:

- derive a fake schedule when none is supplied;
- invent missing player forecasts;
- silently choose competitive-state thresholds;
- translate market value into lineup performance;
- infer owner strategy;
- turn team deltas into trade advice;
- persist the live league payload to source control.

These constraints preserve the authority boundaries established by the FSFFL NEXT charter.
