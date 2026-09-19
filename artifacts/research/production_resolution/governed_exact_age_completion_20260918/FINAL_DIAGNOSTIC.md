# FSFFL NEXT — Governed exact-age completion through Shapley diagnostic

Date: 2026-09-18

## Authority

Executed under Management Authorization — Resolve Two DOB Conflicts and Resume.

Authorized conflict resolutions applied exactly:
- KC Concepcion: 2004-09-23.
- Jadarian Price: 2003-10-09.

A2 age rule remained frozen:
`age_years = (2026-09-01 - DOB).days / 365.2425`, no rounding, no position-specific adjustment.

## Gate 0 — exact-age completion

PASS.

- resolved rows: 35/35
- reference date: 2026-09-01
- canonical 35-row payload SHA-256: `06b5188ead67f52f62c34117bb861a2dc3a920dc83162a9ce2ba50970df692cf`
- joined frozen Year-1 universe: 335/335 rows have numeric A2 age
- joined universe SHA-256: `5dee244f794cd504a84d1575ed1d5fca5b467e604f682018a850363f7fbd5c0f`
- fields changed: only `player_state.age_years` on the 35 previously-null rows
- reload verification: PASS

## Gate A — complete Y2/Y3 board

PASS.

The exact frozen routed Forecast + M1a + two-prior candidate was executed over all 335 players after the governed age join.

- player count: 335
- horizon rows: 670
- horizons: Y2 and Y3
- rows SHA-256: `723f14076f5d0b8801cfff731c8a533494a9d8bbf98531bf25e2d45a16ce1fe8`
- no players dropped
- no age fallback
- no refit/reselection/routing/coefficient/feature change

## Gate B — replacement-coordinate sentinel parity

PASS.

Compared the eight governed sentinel Y2/Y3 rows against the replacement-coordinate sentinel authority:
- Aaron Rodgers
- Sam Darnold
- Bijan Robinson
- Jahmyr Gibbs
- Puka Nacua
- Christian McCaffrey
- Brock Bowers
- Trey McBride

Maximum absolute difference across persisted numeric sentinel fields: **0.0**.
Required tolerance: `<= 1e-6`.

## Gate C — governed Intrinsic/Shapley

PASS / diagnostic completed.

Executed the unchanged PR #147 Shapley economy:
- universe: 335 players
- permutations: 2,048 per horizon
- base seed: 20260915
- horizon seeds: 20260915 / 20260916 / 20260917
- annual discount: 0.85
- lineup legality: frozen 12-team QB/RB/RB/WR/WR/WR/TE/FLEX/SUPERFLEX structure
- holding cost/B4: absent, unchanged
- market, owner, trade and team-utility inputs: absent

Canonical full-precision ranking payload SHA-256:
`9a77cea3675a4e828f7582db905e853a8d102b664411485db6c7f0465c5ff753`

The complete 335-player ordered ranking is persisted in:
`intrinsic_shapley_complete_rankings.psv`.

## Sentinel extract

| Player | Overall rank | Raw Intrinsic |
| --- | ---: | ---: |
| Bijan Robinson | 6 | 607.255264961471 |
| Jahmyr Gibbs | 8 | 587.282190492331 |
| Sam Darnold | 16 | 520.588715862062 |
| Puka Nacua | 18 | 517.147759716306 |
| Christian McCaffrey | 28 | 463.315493010300 |
| Aaron Rodgers | 58 | 330.566338310080 |
| Trey McBride | 65 | 315.082677702786 |
| Brock Bowers | 79 | 269.363804083419 |

Nearby neighborhoods are available directly from the complete ordered ranking; no post-hoc ranking edits were made.

## Newly age-completed examples

- Fernando Mendoza: rank 100, 232.498453388838
- Jeremiyah Love: rank 70, 296.178805808976
- Jadarian Price: rank 140, 166.955149550266
- KC Concepcion: rank 148, 152.302402765710
- Carnell Tate: rank 150, 151.953230125622
- Makai Lemon: rank 177, 119.983120099993

These are diagnostic outputs, not promotion judgments.

## Protected-boundary verification

No:
- refit or retraining;
- Forecast reselection;
- coefficient/routing/feature change;
- age fallback;
- named-player model override;
- Shapley mechanics change;
- main modification;
- PR #147 modification;
- merge;
- deploy;
- promotion.

Execution stops here for management review as authorized.
