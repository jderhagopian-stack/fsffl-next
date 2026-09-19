# FSFFL NEXT - Replacement Identity / Materialization Coordinate

Checkpoint date: 2026-09-18

Authority: research-only data engineering

Status: **PASS - NEW 335-ROW REPLACEMENT COORDINATE CONSTRUCTED, HASHED, RELOADED, AND AUDITED - STOP**

## Decision boundary

This is a **new replacement evidence coordinate** created after exact recovery of the original current-player identity bridge failed. It is not the recovered original bridge and must never be represented as such.

The frozen model remains unchanged. No training-window comparison, refit, retraining, tuning, feature addition, coefficient change, Y2/Y3 Forecast materialization, sentinel Forecast parity, Intrinsic/Shapley execution, or ranking inspection occurred.

## Coordinate

- Coordinate: `replacement-identity-materialization-v1:2026-09-18T17:06:21Z`.
- Frozen left-hand population: exactly **335** rows from `year1-current-governed-2026:2026-09-18T09:42:31.889752+00:00`.
- Row-material SHA-256: `1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56`.
- Stable population SHA-256: `095d09458bfe021e7b7075281e8430573514c6d1e5c2dae3d25430f555ceba4b`.
- Fresh-read reload: **PASS**, 335 rows and identical row/population hashes.

## Frozen provider identity evidence

Identity snapshot coordinate: `nflverse-players-20260918T123430Z+roster-2025-20260314`.

- NFLverse `players.csv`: release asset `572597132`, updated `2026-09-18T12:34:30Z`, SHA-256 `801d5fec2fc21c54ad585415e8e551ae9d1de7c601a8c3768504b7ce59b579b6`.
- NFLverse `roster_2025.csv`: release asset `373640814`, updated `2026-03-14T07:33:08Z`, SHA-256 `531ee5de386037bb17de3e3e3d50f7b4ed08789526bbaae9876fdd3dfb4d04ad`.
- The persisted governed snapshot contains the exact 916 roster-limited skill-player identity records and fields used by the matcher, plus raw source URLs, asset identifiers, timestamps, and hashes. Raw upstream files are not redistributed.

## Deterministic identity result

Predeclared rule order was applied without manual adjudication:

| Mapping status | Rows |
|---|---:|
| `DIRECT_ID` | 73 |
| `CANONICAL_CROSSID` | 0 |
| `EXACT_NAME_POSITION` | 227 |
| `AMBIGUOUS` | 0 |
| `UNMATCHED` | 35 |
| **Total** | **335** |

No qualifying pre-task durable canonical cross-ID table was found in the repository. Exact name+position matches required one provider candidate, reverse uniqueness on the current side, and no accepted GSIS collision.

All 300 accepted historical identifiers are unique. A post-hoc provider cross-ID audit, which was not used as a mapping rule, agreed on Sleeper identity for **300/300** accepted matches with zero disagreements.

The 35 unmatched rows all have reason `NO_EXACT_NAME_POSITION_MATCH`. They remain explicit unmatched identities; none was converted into ordinary no-history coverage.

## Frozen 2024/2023 PIT inputs

The governed Phase2 player-season panel was used at SHA-256 `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`. The frozen age/state residual method was parity-checked against all 619 persisted 2022 horizon-1 rows:

- maximum absolute residual-z difference: `4.440892098500626e-16`;
- scope mismatches: `0`;
- missing rebuilt rows: `0`;
- status: **PASS**.

Each 2023 residual uses only seasons before 2023. Each 2024 residual uses only seasons before 2024. No parameter was estimated for the selected Forecast.

| Prior-history result | Rows |
|---|---:|
| Two genuine prior seasons | 199 |
| Missing 2023 only | 46 |
| Missing 2024 only | 1 |
| No 2024 or 2023 history | 54 |
| Identity unmatched | 35 |
| **Total** | **335** |

PIT rows are available for 245 players in 2024 and 200 players in 2023. Uncovered continuous feature values are persisted as neutral zero with `prior2_coverage=0` and an explicit reason, following the already-frozen feature contract. This task does not decide whether downstream completeness is sufficient.

## Eight-sentinel identity audit

| Sentinel | Mapping | GSIS | 2024 | 2023 | Prior-two |
|---|---|---|---|---|---|
| Aaron Rodgers | `DIRECT_ID` | `00-0023459` | Yes | Yes | Covered |
| Sam Darnold | `DIRECT_ID` | `00-0034869` | Yes | Yes | Covered |
| Bijan Robinson | `EXACT_NAME_POSITION` | `00-0038542` | Yes | Yes | Covered |
| Jahmyr Gibbs | `EXACT_NAME_POSITION` | `00-0039139` | Yes | Yes | Covered |
| Puka Nacua | `EXACT_NAME_POSITION` | `00-0039075` | Yes | Yes | Covered |
| Christian McCaffrey | `DIRECT_ID` | `00-0033280` | Yes | Yes | Covered |
| Brock Bowers | `EXACT_NAME_POSITION` | `00-0039338` | Yes | No | Not covered: missing 2023 |
| Trey McBride | `EXACT_NAME_POSITION` | `00-0037744` | Yes | Yes | Covered |

No sentinel Y2/Y3 Forecast value was computed or compared.

## Persisted artifacts

- `replacement_identity_materialization_coordinate.json`: row-complete 335-player coordinate.
- `provider_identity_snapshot.json`: governed provider identity snapshot/provenance package.
- `manifest.json`: inputs, rules, hashes, outputs, and independence declaration.
- `collision_unmatched_audit.json`: all unmatched rows and mapping audits.
- `sentinel_identity_audit.json`: eight-sentinel identity/PIT status only.
- `pit_coverage_audit.json`: coverage and frozen-method parity.
- `reload_verification.json`: fresh-read deterministic verification.
- `RECONSTRUCTION.md`: exact reconstruction and verification instructions.

## Stop boundary

**STOP.** Management must decide whether the reported completeness is sufficient before any downstream use. Do not materialize the 335-player Y2/Y3 Forecast board, run sentinel Forecast parity, run Intrinsic/Shapley, tune, refit, implement, promote, merge, or deploy under this authority.
