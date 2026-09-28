# 2026-09-28 — Atomic Intelligence Publication Contract

## Status
**MANAGEMENT DIRECTIVE — ROOT-CAUSE RUNTIME CORRECTIVE**

## Why this supersedes symptom-only fixes
Physical iPhone/Safari testing on live PR #283 shows the product can report **Intelligence current** while product surfaces simultaneously expose incompatible/intermediate states:
- League Atlas: Simulation unavailable while global intelligence reports current.
- Franchise: Broad Market available, then unavailable one minute later.
- Franchise: FSFFL Intrinsic unavailable -> preparing during the same browsing session.
- League Value Map: FSFFL Intrinsic ready while Broad Market is unavailable / 0 players covered.
- The same live session therefore exposes different stages of one reconciliation lifecycle across surfaces.

Current code confirms the architectural cause:
- `PrivateBetaRuntimeStore.set_forecast_evidence()` replaces the live runtime context immediately and sets `simulation_analytics=None` and `value_evidence=None`.
- `set_simulation_analytics()` then replaces the live context again and keeps `value_evidence=None`.
- reconciliation currently calls these setters sequentially before final presentation promotion.
- presentation continuity serves stale last-good payloads only when `served.league_state_id != current.state_id`; it does not protect a same-State intelligence refresh.
- `/api/intelligence/status` reports stage readiness separately from product capability/presentation readiness, allowing a green/current status to disagree with rendered surfaces.

Therefore the remaining problem is not one isolated PI timeout. The runtime is exposing a **working reconciliation generation** directly to readers.

## Required architecture
Separate **working reconciliation** from **published intelligence**.

### 1. Published generation
Maintain one immutable, user-visible intelligence generation for the selected league/team. It owns the exact compatible set of:
- canonical State identity;
- Forecast identity/authority;
- Simulation identity or governed terminal unavailability;
- Broad Market / current Value identity or governed terminal unavailability;
- FSFFL Intrinsic identity/status;
- presentation manifest/surface payloads;
- publication generation/fingerprint.

All normal product reads must resolve from this published generation.

### 2. Working generation
Forecast/Simulation/Value/Intrinsic reconciliation runs against a non-user-visible working generation. Intermediate steps must not evict or mutate the currently published generation.

Do not publish Forecast first and blank Simulation/Value while later phases run.

### 3. Atomic promotion
Only after the replacement generation reaches a coherent terminal state and required presentation payloads are built/durably checkpointed should one atomic promotion make it visible.

A terminal generation may truthfully contain an unavailable capability when authority forbids it (for example Simulation under partial Forecast authority). That is different from a capability disappearing merely because reconciliation is mid-flight.

If replacement reconciliation fails/interruption occurs, leave the prior compatible published generation intact.

### 4. Same-State continuity
Last-good/published continuity applies to same-State intelligence refreshes as well as changed-State reconciliation. State equality must not force users to observe intermediate derived-artifact invalidation.

### 5. Status semantics
The global banner must describe the **published generation**, not merely job/stage progress.

Required semantics:
- `Updating intelligence — serving last good` while a working generation is building and prior compatible publication remains visible.
- `Intelligence current` only when the current published generation matches the target State and the product-required capability/surface contract is coherently terminal.
- If one or more product-required capabilities are authoritatively unavailable, show a truthful limited/partial state rather than an unqualified green current label.
- Do not allow global current/readiness copy to contradict the visible surface payloads.

### 6. Surface identity
Expose a lightweight `publication_generation_id` / fingerprint in product-context and surface payload diagnostics so acceptance can prove Home, Franchise, League Atlas, Market, Player Intelligence/value lenses are reading one coherent published generation.

## Acceptance requirements
Add deterministic regressions and hosted/browser acceptance proving:

1. **Same-State refresh continuity:** begin from a fully published generation, trigger reconciliation, and repeatedly read Franchise, League Atlas, Market/value lenses and PI while Forecast -> Simulation -> Value -> Intrinsic work occurs. Previously visible compatible data must not disappear or regress to preparing/unavailable merely because replacement work is incomplete.
2. **Cross-surface generation consistency:** all normal surfaces observed in one publication interval report the same generation ID/fingerprint.
3. **Failed refresh:** inject provider/build failure after Forecast or Simulation work begins; prior published generation remains intact and usable.
4. **Successful refresh:** replacement surfaces switch coherently only after terminal checkpoint/presentation promotion.
5. **Restart/interruption:** restart during working reconciliation restores the last published generation, never the half-built working generation.
6. **Truthful partial authority:** legitimate governed Simulation/Forecast partiality remains explicit and does not become fake full readiness.
7. **Status/UI contract:** global readiness cannot say `Intelligence current` while required visible surfaces are building/unavailable due only to in-progress reconciliation.
8. **Physical-style read overlap:** PI/history and other persisted reads remain responsive while background reconciliation executes; foreground reads consume published evidence rather than blocking on working-generation materialization.
9. Preserve PR #280 foreground latency/memory gains and PR #283 Forecast<->Simulation dependency correctness.

## Scope
This is a narrow runtime/publication correction, not a Forecast/Value/Intrinsic model change and not a new product workstream. Do not reopen Research, ROS implementation, Long-Term Intrinsic, Market model semantics, or provider authority rules until this contract passes hosted acceptance.

## Terminal requirement
Do not return on a local test or PR alone. Merge/deploy the corrected exact SHA and run the full hosted FSFFL -> Hodor -> FSFFL journey plus same-State refresh/read-overlap acceptance. Then require physical iPhone/Safari smoke validation before Management closes runtime stabilization.
