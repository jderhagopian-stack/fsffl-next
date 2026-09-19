# FSFFL NEXT — Frozen Identity/Materialization Dependency Recovery

Checkpoint date: 2026-09-18

Authority: research-only recovery

Status: **BOUNDED NEGATIVE RESULT — EXACT CURRENT-PLAYER MATERIALIZATION IS NOT REPRODUCIBLE — STOP**

## Outcome

The exact historical training/cutoff machinery and fitted parameters for the selected routed + M1a + two-prior-season candidate were recovered. The original row-level current-player → historical identity dependency was not.

That boundary is decisive. The 335-player current universe can be loaded, but 262 rows lack a persisted direct GSIS reference, and the frozen artifacts do not retain the in-memory bridge that resolved Sleeper identities to historical source keys. The exact 2024/2023 PIT age/state residual inputs are also absent. Re-running name/position matching or fetching current provider data would create a new methodological coordinate, so no current-player Y2/Y3 materialization was attempted.

No refit, retraining, reselection, Year-2/Year-3 materialization, sentinel parity, Shapley, or fresh provider fetch occurred.

## Recovered frozen machinery

- Candidate: fixed routed Forecast + M1a + two-prior-season consistency.
- Routing: QB → A2+C+D; RB/WR/TE → A2+D.
- Scope: adjust positive-state conditional means only; persistence and state probabilities remain frozen.
- Training inclusion: positive source/target transitions satisfying `source_season + horizon <= evaluation cutoff`; historical source rows through 2022.
- M1a: `BayesianRidge(fit_intercept=False)` of target within-state residual z on current within-state residual z.
- Consistency response: target residual z minus M1a prediction.
- Consistency features: global mean/gap/coverage plus mean/gap × position deviations; no third prior season, hard tier, role/security, interaction, or named-player rule.
- Prior inputs: `mean(z[t-1],z[t-2])`, `abs(z[t-1]-z[t-2])`, and coverage. Continuous inputs are zero unless both genuine prior seasons exist. Training-only population moments (`ddof=0`) standardize covered rows.

Exact fitted current-diagnostic parameters:

| Item | Y2 | Y3 |
|---|---:|---:|
| Training rows | 5,974 | 4,781 |
| Source seasons | 2005–2022 | 2005–2022 |
| M1a coefficient | 0.07939942531895901 | 0.07812314495946265 |
| Prior-two coverage | 0.5033478406427854 | 0.4862999372516210 |
| Mean μ / σ | 0.18051735619583884 / 0.8250069242245336 | 0.2161366754026284 / 0.8286552914628750 |
| Gap μ / σ | 1.109345052497919 / 0.9101986764652646 | 1.104921589465751 / 0.8918729700175280 |

Coefficient order: `mean_global, gap_global, coverage_global, mean_dev_QB, gap_dev_QB, mean_dev_RB, gap_dev_RB, mean_dev_WR, gap_dev_WR, mean_dev_TE, gap_dev_TE`.

- Y2: `[0.104407393, 0.0256567937, 0.026386248, 0.158161626, -0.0501651272, -0.00347923962, -0.000109866463, 0.0189868866, -0.0249518009, -0.0206613761, 0.0522830842]`
- Y3: `[0.0896474572, 0.00230448058, 0.0208369151, 0.180179816, -0.057293661, -0.00910620769, -0.0241324898, 0.0336007196, -0.0225647051, -0.00887356736, 0.000142033387]`

These are reproduced from the frozen diagnostic, not re-estimated.

## Recovery surfaces exhausted

| Surface | Scope | Result |
|---|---|---|
| Git refs/history | 179 refs; 2,583 reachable commits; all fetched remote refs and tags | No final materializer, 335-row identity bridge, or row-complete historical input table |
| Stashes/unreachable Git | 0 stashes; unreachable commits `26883f6`, `b93cdaa`, `c2c1437` | Earlier checkpoints only; no missing dependency |
| Durable repo artifacts | All production-resolution, Phase34, Phase2, activation, and history-linked artifacts | Frozen fit recovered; row-level resolved source keys absent |
| Activation Actions run | Run `35145456513`, artifact `10467264159`, ZIP SHA-256 `3866d653…95ca5` | Exact artifact recovered; contains current facts and frozen I1 files only |
| Year-1 Actions run | Run `35330898624`, artifact `10541375155`, ZIP SHA-256 `c23fed64…9ee7` | Exact 335-player Year-1 artifact recovered; no historical mapping or prior residuals |
| Actions logs/caches | Successful activation/freeze/persist job logs; workflow definitions | `/tmp/private_beta_completed_source_points.csv`, `/tmp/nflreadpy-cache`, and in-memory bridge were not uploaded; no `actions/cache` persistence step |
| Local remnants | `/workspace/scratch`, `/mnt`, `/tmp`, all registered worktrees | Only older routed-sentinel runner/report and Phase2 archive; not the selected final dependency |

The connected GitHub interface does not expose the Actions cache-list endpoint. This does not hide an identified durable cache: the historical workflow contains no `actions/cache` save/restore step, and its upload step names only `artifacts/implementation/private-beta-activation/*`.

## Exact missing dependency

Required for provenance-identical materialization:

1. the original frozen 335-row Sleeper → historical source/player-key crosswalk; and
2. the corresponding exact 2024 and 2023 PIT age/state residual inputs (or a row-complete 335-player table already containing them).

The activation builder created a `completed-source-roster-unique-name-position-v1` bridge from contemporaneous `nflreadpy` players/2025 rosters and Sleeper data. It persisted only aggregate counts—479 recovered stable IDs, 155 existing stable IDs, 179 without a completed-source roster match—not the resolved rows or exact provider snapshots. `current_i1_facts_2026.json` keeps `sleeper:<id>` as `source_player_id`.

The later governed Year-1 table has 335 rows, but only 73 include direct GSIS references. The remaining 262 cannot be mapped provenance-identically from frozen evidence. Among the eight named sentinels, only Aaron Rodgers (`00-0023459`), Sam Darnold (`00-0034869`), and Christian McCaffrey (`00-0033280`) have direct GSIS references; Bijan Robinson, Jahmyr Gibbs, Puka Nacua, Brock Bowers, and Trey McBride do not.

## Dependency classification

| Dependency | Classification |
|---|---|
| Historical cutoff procedure | Recovered exact |
| Frozen M1a/consistency fit parameters | Recovered exact |
| Later 335-player Year-1 universe | Recovered exact, but explicitly a fresh later coordinate |
| Original 335-row identity bridge | Not persisted |
| Exact 2024/2023 PIT inputs for the 335 | Not persisted |
| Ephemeral runner files/provider snapshots | Destroyed or inaccessible; equivalence unproven |
| Exact current-player materialization | Not reproducible without a new methodological choice |

## Minimum governance decision

The smallest viable next authorization is not a “recovery” authorization. Management would need to approve a replacement identity/materialization coordinate: a named/versioned provider snapshot, deterministic collision and unmatched-player policy, and durable persistence of the full 335-row crosswalk plus 2024/2023 PIT inputs. Any such decision creates a new evidence coordinate and must not be represented as the frozen original.

## Integrity anchors

- Current I1 facts: `dbea7f754e0910a83a85518880a5e3f649579116a205f9d30d8a4c9f39a7932d`.
- Phase2 panel: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`.
- Corrected Phase2 age/state rows: `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`.
- Final holdout result: `b69de5633a320e74e702d7b63368df2e7d1ff9e971745d6ed20060dae3a89a9b`.
- Final sentinel result: `6f001aef726f43e517c014bfdfca56dfb79ae66dd2095ed0a902df6add4d9677`.

**STOP.** Do not substitute a different training window, refit, reconstruct identities heuristically, fetch a fresh provider snapshot, materialize Y2/Y3, run sentinel parity, or run Shapley under this authority.
