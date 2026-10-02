# 2026-10-02 — Startup / Refresh Sequencing Corrective

## Status
**MANAGEMENT DIRECTIVE — NARROW BETA-AVAILABILITY / LIFECYCLE CORRECTIVE**

This directive is triggered by contradictory physical + hosted evidence on the accepted production runtime. It reopens only the startup/manual-refresh reconciliation lifecycle. It does **not** reopen Forecast, Simulation 2.0 model semantics, Value, origin-aware pick Value design, Market, or previously accepted unrelated platform layers.

Origin-aware draft-pick Value PR #335 is held at its current safe checkpoint until this corrective closes.

## Physical / hosted evidence
On the live Render service `fsffl-next-private-beta` running merged #330:

- service cold-started around 2026-10-02T14:38Z;
- startup restore reported State present, Forecast present, Value present, Simulation absent;
- manual browser refresh was accepted at 2026-10-02T14:50:28Z;
- first reconciliation reached `simulation_build_complete` at 14:57:49Z;
- immediately afterward that reconciliation logged `job_aborted` before publication;
- a replacement reconciliation began at 14:57:50Z;
- replacement Simulation completed at 14:59:56Z;
- Value completed at 15:00:00Z;
- Intrinsic reconciliation completed at 15:00:27Z;
- coherent publication completed at 15:01:58Z;
- physical Safari UI moved 1/7 -> 6/7 -> 7/7 only after the replacement pass.

Resource evidence:
- first pass peak RSS observed: **445,063,168 bytes**;
- engineering budget: **429,496,720 bytes**;
- Render hard limit: **536,870,900 bytes**.

The user-visible result recovered, but a single manual refresh performed duplicated expensive work and discarded a completed Simulation before publication. That is not an accepted steady-state lifecycle.

## Objective
Make startup + refresh reconciliation deterministic and monotonic:

1. one accepted refresh/lifecycle owner for one unchanged league/team/State generation;
2. equivalent triggers coalesce rather than replace;
3. a completed heavy phase is not discarded unless a **real governed dependency changes**;
4. unrelated Behavioral/background work cannot supersede the active intelligence publication generation;
5. progress/readiness advances monotonically for the active generation and cannot present a long-lived stale 1/7 state while a different generation owns the work;
6. atomic publication remains the only transition to the new coherent generation;
7. resource usage stays within the established engineering memory budget in the representative physical refresh flow.

## Required trace
Reproduce and trace the exact live path, including:
- cold-start restore;
- startup reconciliation decision;
- `GET /api/connect/sleeper/background/current`;
- manual `POST /api/connect/sleeper/background/refresh`;
- reconciliation generation/league/team ownership;
- State resource boundary;
- Behavioral job handoff;
- heavy-work coordinator queue/admission;
- Simulation completion;
- Value/Intrinsic;
- working-generation cleanup;
- atomic publication;
- client status polling/readiness presentation.

Identify the exact event/ownership check that caused the first post-Simulation `job_aborted`. Do not infer the cause only from the `active=behavioral` log field.

## Governing invariants
- Browser polling/status reads are observational and may never create a replacement generation.
- Repeated/equivalent refresh requests for the same league/team/material State must coalesce.
- A true State change may replace work only through the governed lifecycle boundary and must preserve last-good publication.
- Behavioral work may queue/execute under the process-wide coordinator but must not mutate intelligence reconciliation ownership.
- Cleanup from an older job must remain generation-conditional.
- Restored partial intelligence may trigger exactly one required reconciliation path, not competing startup + browser paths.
- 50,000 Simulation authority is unchanged.
- Do not reduce work by weakening Forecast/Simulation/Value/Intrinsic authority.

## Deterministic regressions
Add focused race/lifecycle coverage for at least:
1. cold-start partial restore + immediate manual refresh;
2. startup reconciliation and equivalent browser refresh coalescing;
3. Behavioral work beginning while Simulation reconciliation is active;
4. Simulation completes while a queued non-reconciliation heavy job exists;
5. stale/older reconciliation cleanup cannot abort or erase the current working generation;
6. repeated background/current polling cannot change ownership;
7. one material State change correctly replaces old work and preserves last-good;
8. terminal publication occurs once and progress/readiness is monotonic;
9. no duplicate 50k Simulation for an unchanged target generation.

## Resource gate
The corrective must explain the 445,063,168-byte peak and return the representative hosted refresh to **<= 429,496,720 bytes** engineering budget unless Management explicitly approves a revised budget based on new evidence. Do not treat staying below Render's hard OOM limit as sufficient.

## Validation / promotion
This is a Tier C lifecycle/resource corrective:
- focused deterministic race/lifecycle regressions;
- full CI;
- exact-head P1/P2 review;
- one targeted hosted cold-start/partial-restore -> manual-refresh acceptance;
- verify one coherent build, no duplicate Simulation, no restart, monotonic progress to 7/7, publication continuity, and memory budget;
- one physical iPhone/Safari confirmation if hosted telemetry cannot prove client readiness sequencing.

Do not broaden into general startup redesign or unrelated performance tuning.

## Sequencing
Hold PR #335 at its current safe checkpoint. Once this corrective is accepted, rebase/reconcile #335 if needed and resume origin-aware draft-pick Value immediately. Then continue to Long-Term Intrinsic.
