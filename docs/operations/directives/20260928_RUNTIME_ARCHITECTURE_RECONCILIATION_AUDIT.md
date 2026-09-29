# 2026-09-28 — Read-only runtime architecture reconciliation audit

## Purpose

Management is concerned that the live/private-beta runtime evolved away from the founding FSFFL NEXT architecture even though the analytical authority chain remains sound.

Run a **read-only architecture audit**. Do not modify code, docs, branches, PRs, deployment state, persistence, or Render configuration.

This audit may run in parallel with active Implementation because it is review-only.

## Canonical founding architecture

Treat these as primary architectural authority:
- `docs/architecture/overview.md`
- `docs/architecture/authority-boundaries.md`
- `docs/architecture/performance-and-caching.md`
- `docs/architecture/point-in-time-state.md`
- `docs/architecture/api-ui-boundary.md`
- `docs/migration/next-0-exit-review.md`
- `docs/migration/roadmap.md`

Core authority chain:
`Data -> Point-in-Time State -> Forecast -> Value -> Decision -> Search/Optimization -> Analytics/API -> Presentation`.

Important founding principles:
- downstream layers consume upstream authority rather than recreating it;
- valid canonical State is foundational and provider-neutral;
- persistence/cache are implementation mechanisms, not analytical authority;
- cache correctness precedes hit rate;
- expensive work should be reusable and not implicitly rerun from foreground reads;
- API/application layer resolves State and invokes authoritative services;
- UI/presentation must not own hidden analytical logic;
- distributed/runtime complexity should be introduced only when justified.

## Current concern

The product recently regressed from a previously reliable hosted first-load path into a state where:
- Connect League could wait on persistence/checkpoint work after valid Sleeper State already existed;
- browser-local team restoration could silently affect a supposedly fresh session;
- team identity and intelligence job lifecycle could become entangled;
- foreground reads could wait on persisted diagnostic/runtime work;
- restore/persistence/publication correctness grew increasingly complex across PRs #261, #274-#292.

PR #54/`0021aefc...` and PR #56/`a8527e1...` are important historical references because they deliberately kept first-load State usability ahead of persistence.
PR #261/`c57bc39...` is important because later switch/durability safety reintroduced a State-activation durability barrier.
PRs #284-#291 established atomic publication and lifecycle-concurrency protections.
PR #292/`8c162c5a...` is the current first-load recovery corrective and is under hosted acceptance.

## Audit questions

Review current main, relevant history, and current runtime/application code against the founding architecture.

Determine:

1. Which founding architecture principles are still being followed correctly?
2. Where has the runtime/application implementation materially drifted from those principles?
3. Are persistence, caching, restore, publication, team identity, or background orchestration exercising authority they should not own?
4. Does valid canonical State remain independently usable, or are infrastructure concerns incorrectly placed in its critical path?
5. Are Forecast/Simulation/Value being triggered only through explicit application orchestration, or can foreground/read/presentation paths implicitly launch expensive upstream work?
6. Is managed-team identity a clean prerequisite/input to team-dependent intelligence, or is it coupled bidirectionally to job lifecycle?
7. Is last-good restore a recovery optimization, or has it become necessary for normal correctness?
8. Does restart authority remain conceptually separate from live State usability?
9. Are browser-local preferences/session hints appropriately presentation/session concerns, or can they silently create server-side analytical identity?
10. Does atomic publication preserve the original authority chain, or has the implementation added unnecessary coupling around it?
11. Did any later runtime fix solve a real reliability problem by violating a more fundamental architectural boundary?
12. Is PR #292 directionally restoring the founding contract, or only patching symptoms?
13. What is the **smallest architectural simplification** that would prevent this class of regression while preserving the safety gains from #261/#284-#291?
14. Which current mechanisms are essential, which are accidental complexity, and which should eventually be removed or demoted from the critical path?

## Scope discipline

- Do **not** re-audit Forecast/Value/Decision model quality unless a runtime boundary directly violates their authority.
- Do **not** propose a broad rewrite merely because code is complex.
- Do **not** optimize for number of findings.
- Prefer one violated architectural invariant that explains several symptoms over multiple endpoint-specific observations.
- Distinguish confirmed code-path violations from design risk or conjecture.
- Preserve valid safety properties from #261 and #284-#291 unless evidence shows they conflict with the founding architecture.
- Treat PR #292 as current implementation under test, not automatically accepted.

## Deliverable

Return a concise but substantive management report with:

1. exact current main SHA reviewed;
2. founding principles checked;
3. confirmed architectural deviations, each with concrete code/history evidence and practical user/product consequence;
4. areas that remain architecturally sound;
5. assessment of whether the recent failures are primarily:
   - analytical-architecture failure,
   - runtime/application architecture drift,
   - implementation defects within a sound runtime design,
   - or a combination;
6. smallest corrective architecture, expressed in plain language and then technical terms;
7. which current safeguards must be retained;
8. which coupling/complexity should be removed or moved off the critical path;
9. whether PR #292 moves the system toward or away from that target;
10. a bounded follow-up plan, separated into:
    - must fix before runtime stabilization closes;
    - safe to defer until after availability is restored.

Do not modify anything. No PR, no deploy, no docs edits. Return findings to Management only.
