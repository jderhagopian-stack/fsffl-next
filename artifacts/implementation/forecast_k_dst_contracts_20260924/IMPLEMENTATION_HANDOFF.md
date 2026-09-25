# FSFFL NEXT — Forecast/Product K/DST Implementation Checkpoint

Date: 2026-09-24  
Workstream: Forecast / Product Implementation  
Research authority: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`  
Implementation PR: #215 — MERGED  
Code acceptance head: `c57c0423f2fb982b2ece88a0d112542ed5ed1011`  
Reconciled PR head: `e918429c41310226a8ad73354db1280ecc9636b3`  
Canonical merge SHA: `407c1bf85e5dc75f92b9906719f82bcd11d97c31`

## Terminal workstream state

**BLOCKED — FORECAST / PRODUCT IMPLEMENTATION — EMPIRICAL EVIDENCE GATE**

The authorized bounded code work that can be completed without inventing upstream evidence is implemented, regression-clean, reconciled with concurrent Market operating-state changes, and merged to canonical main. Production K/DST Forecast authority cannot advance to the next implementation stage until the retained evidence gates below are satisfied.

## Accepted implementation scope

### Stage 1 contracts / scoring
- shared canonical NFL team aliases and roster-to-Forecast D/ST identity boundary;
- K remains a player Forecast subject;
- D/ST is a canonical NFL team-season unit;
- player-shaped D/ST Forecast observations are rejected;
- team-unit Forecast observations and bundles are separately typed;
- explicit K and D/ST raw metric vocabularies;
- rule-level evidence coverage with source independence groups;
- exact vs exact-derived K scoring coverage;
- no 50+ heuristic split into 50–59 / 60+;
- D/ST linear event scoring plus per-game distributional bucket scoring;
- team `def_st_*` semantics kept distinct from player `st_*`;
- active missing `fum_lost` evidence withholds authoritative fantasy points;
- synthetic zero is allowed only as explicit fixture evidence, never as provider/runtime substitution;
- CBS missing FL no longer becomes a manufactured 0.0;
- Sleeper unrostered universe includes K but not D/ST pseudo-player Forecast subjects.

### Stage 2 non-promoting harness
- deterministic kicker realized outcomes from nflverse-style PBP;
- blocked FG/PAT encoded as kicker misses;
- kick-distance completeness defects retained explicitly;
- conservative directly observable D/ST realized-event reconstruction;
- season-error benchmark harness requiring at least two independent sources;
- weekly-volatility benchmark from realized game scores, not season mean / 17.

### Existing bootstrap invariant exercised
- the same immutable annual raw snapshot can be replayed under different league scoring without changing its raw hash, source IDs, or provider effective timestamps.

## Acceptance evidence

On code head `c57c0423f2fb982b2ece88a0d112542ed5ed1011`:
- full CI: **1517 passed, 1 warning**;
- PR164 focused corrective regression: **89 passed, 1 warning**;
- Corrective live provider numerical trace: **PASS via expected active-rule evidence quarantine**;
- Live Forecast corrective trace: **PASS** (the workflow's persistence-dependent execution remains subject to its existing environment boundary);
- Private-beta Intrinsic live diagnostics: **PASS** on the reconciled head;
- all five executable PR workflows passed again after reconciliation with current main;
- PR #215 merged successfully to main.

The live numerical trace's authoritative ensemble still fails closed when the acquired providers do not supply complete evidence for the active `fum_lost` rule. The workflow records that as an expected evidence quarantine; runtime authority is not weakened.

## Authority explicitly not promoted

No implementation in PR #215 claims or creates:
- a production K/DST live provider ensemble;
- a production K or D/ST uncertainty coefficient;
- a qualifying 2026 K/DST preseason baseline;
- historical K/DST calibration from one source;
- current/post-opener data backdated as preseason;
- unresolved Sleeper D/ST scoring semantics;
- K/DST Value, Simulation, Decision, Search, or Presentation truth.

## Blocking evidence dependencies

1. **Historical independent source #2:** one recoverable dated source is insufficient to fit/promote the governed K/DST season-error benchmark.
2. **Provider rights/content health:** production adapters require validated usage rights plus the content-aware health contract from Research.
3. **Sleeper scoring truth fixtures:** obscure D/ST attribution/bucket semantics require exact platform validation before promotion.
4. **2026 preseason K/DST authority:** no qualifying two-source point-in-time raw package is proven. K/DST preseason comparison must remain unavailable unless such evidence is established.

Because Stage 3 live-provider work is gated by these dependencies, Stage 4 migration/downstream promotion and Stage 5/6 lifecycle completion must not be started speculatively.

## Post-merge evidence-gate check

A bounded recovery/rights check was executed after merge rather than assuming the blocker:
- dated Razzball 2024 material confirms K/DEF preseason projections existed, but its projection links now resolve to mutable current endpoints rather than an immutable 2024 raw corpus;
- CBS historical-looking year paths can serve current/week projection content and therefore are not PIT proof;
- currently published Razzball and CBS terms are non-commercial absent permission, and Sleeper's API documentation requires licensing discussion for commercial use;
- official Sleeper support documentation confirms points-allowed and team-vs-player special-teams semantics at a high level, but exact weekly truth fixtures remain required for unresolved obscure attribution.

Durable evidence: `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`.

No qualifying second historical K/DST PIT source was recovered in this check, so the empirical gate remains red.

## Resume condition

Resume this workstream only when Management supplies or authorizes access to qualifying evidence that clears the relevant Research gate. Do not substitute one-source calibration, offensive-player coefficients, aggregate-source double counting, guessed D/ST bucket math, or synthetic/backdated preseason evidence.
