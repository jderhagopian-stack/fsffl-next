# FSFFL NEXT — Private-Beta Runtime Architecture Regression Baseline

Updated: 2026-09-27

## Authority / purpose

This artifact records the implementation-side regression evidence required by the
canonical private-beta runtime architecture acceptance gate.

It does **not** authorize model changes and does not use PR #235 as a code rollback
target. PR #235 is the Management-selected behavioral usability control.

## Behavioral control

Last demonstrably usable control:

- PR #235
- merge SHA: `3c252aedb5974f40fabe2c16cce01e8e106a2b74`
- Render deploy: `dep-dar9kg142hec73dglcq0`
- deployed 2026-09-25T15:58:56Z; live 2026-09-25T16:00:32Z

Management's accepted control behavior:
- persisted Forecast / Simulation / Value repeatedly restored across restart;
- Home / Franchise were populated and responsive;
- startup did not automatically launch heavy intelligence work;
- Market foreground latency was still poor and is not treated as accepted performance.

## Structural regression delta to pre-corrective current main

Representative source growth from PR #235 merge to the pre-corrective current
runtime:

| File | PR #235 lines | Pre-corrective lines | Structural change |
| --- | ---: | ---: | --- |
| `product/runtime.py` | 574 | 778 | dual-state/pending ownership and compatibility logic |
| `product/persistent_runtime.py` | 319 | 494 | last-good restore/migration and restart orchestration |
| `persistence/session.py` | 307 | 543 | per-league last-good and multi-layer restore paths |
| `product/persistent_webapp.py` | 240 | 589 | automatic hosted acceptance, Intrinsic/readiness composition |
| `product/background_jobs.py` | 355 | 386 | expanded lifecycle/recovery semantics |
| `product/private_beta_shapley_runtime.py` | 430 | 685 | durable/reusable Intrinsic orchestration |
| `product/player_intelligence.py` | 802 | 965 | expanded PI/historical surface behavior |
| `product/player_intelligence_routes.py` | 306 | 328 | player-history background lifecycle |

The static `session_recovery.js` file was unchanged across that control boundary.
That makes a client bootstrap-only explanation less plausible than server-side
retained-object and concurrent-work regressions.

## Pre-corrective memory ownership

The pre-corrective runtime could simultaneously retain, for one user:

1. current `LeagueState + Forecast + Simulation + Value`;
2. `served_intelligence` containing a second full prior
   `LeagueState + Forecast + Simulation + Value`;
3. a pending reconciliation object containing another full
   `LeagueState + Forecast (+ Simulation)`.

This is materially different from the PR #235 runtime, which did not have the
full `served_intelligence` graph.

Separate executors also allowed overlapping high-RSS work:
- core intelligence jobs;
- Intrinsic / Shapley;
- Player Intelligence history;
- Behavioral history;
- persistence checkpointing.

The hosted composition additionally registered an unconditional startup
background product-acceptance path that could initiate full Intrinsic/Shapley
work immediately after restore. PR #235 startup did not do this.

## Render resource evidence

Service memory limit:
- `536,870,900` bytes (~512 MiB).

New acceptance budget:
- at least 20% headroom;
- maximum accepted peak: approximately `429,496,720` bytes (~409.6 MiB).

### PR #235-era control window

Window: 2026-09-25 16:00Z–17:40Z.

Observed examples:
- instance `...-b99fm`: approximately 225–229 MB for its stable interval;
- instance `...-md5ct`: approximately 304–336 MB after warm-up;
- instance `...-dkh2g`: climbed through ~431 MB and peaked near **504 MB**
  under a heavier workload.

Therefore PR #235 is a **usability control**, not evidence that every historical
workload satisfied the new memory budget.

### PR #270 incident window

PR #270 merge:
- `2c63a9b05225759ba521da3e75fb65146b30fbbe`
- live deploy `dep-dasa5vg473hc73fd8uo0`.

Window: 2026-09-27 05:02Z–12:42Z.

Observed examples:
- instance `...-wc4mn`: ~296 MB after wake, then ~408–421 MB;
- instance `...-mxlq6`: ~388 MB rising to ~444 MB;
- instance `...-757fn`: ~409 MB rising to ~495–500 MB.

Multiple instance identities appeared during the incident window. This is
consistent with the already-recorded recycle/restart evidence; this artifact
does not independently label every replacement an OOM event.

## Corrective representation

PR #271 changes the runtime representation/orchestration rather than model
authority:

- exactly one resident current State-bound Forecast/Simulation/Value graph;
- last-good heavy artifacts remain durable, while RAM retains only
  league/state/as-of/team identity;
- pending reconciliation retains State identity only;
- process-wide heavy-work admission serializes Forecast, Simulation, Value,
  Intrinsic/Shapley, Player History and Behavioral history;
- hosted core intelligence uses one worker;
- PI history background queue/record ownership is bounded;
- superseded Behavioral work is cancellable/stale-checked;
- startup is restore-only;
- hosted product acceptance is explicit/authenticated rather than automatic;
- resource telemetry exposes current RSS, process peak RSS, acceptance budget,
  active heavy owner, and queue depth;
- browser readiness can become full only from the server capability contract.

## Non-goals

This corrective does not:
- alter Forecast math or source authority;
- alter 50,000-run Simulation semantics;
- alter Value / Intrinsic math;
- reopen K/DST research;
- alter Decision/Search semantics;
- solve Market foreground latency;
- treat page-specific 502/429 handling as the architectural fix.

## Acceptance still required

Before terminal closeout:
- full CI/focused workflows green on final reconciled head;
- merge current main without conflict;
- Render cold deploy;
- restore-first user path before heavy sync;
- complete hosted cold-wake/user journey;
- no process recycle during acceptance;
- peak RSS <= ~429 MB;
- no duplicate heavy owner;
- no recovery-induced 5xx/429;
- reload during reconciliation preserves canonical roster/State;
- manual Refresh Intelligence remains State-first;
- FSFFL ↔ Hodor ↔ FSFFL works without stale cross-league evidence;
- repeated PI/history uses durable reuse with lower work;
- Intrinsic reattaches/reuses without avoidable Shapley recomputation;
- one readiness authority remains truthful across shell/Franchise/PI.
