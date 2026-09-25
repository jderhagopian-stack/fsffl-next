# FSFFL NEXT — Forecast/Product K/DST Implementation Checkpoint

Date: 2026-09-24  
Workstream: Forecast / Product Implementation  
Research authority: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`  
Implementation PR: #215  
Code acceptance head: `c57c0423f2fb982b2ece88a0d112542ed5ed1011`

## Terminal workstream state

**BLOCKED — FORECAST / PRODUCT IMPLEMENTATION — EMPIRICAL EVIDENCE GATE**

The authorized bounded code work that can be completed without inventing upstream evidence is implemented and regression-clean. Production K/DST Forecast authority cannot advance to the next implementation stage until the retained evidence gates below are satisfied.

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
- PR was mergeable at acceptance check.

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

## Resume condition

Resume this workstream only when Management supplies or authorizes access to qualifying evidence that clears the relevant Research gate. Do not substitute one-source calibration, offensive-player coefficients, aggregate-source double counting, guessed D/ST bucket math, or synthetic/backdated preseason evidence.
