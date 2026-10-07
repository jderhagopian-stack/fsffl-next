# Worker Bootstrap

This file is the repository-root entry point for every worker, including Management successors. Begin here before acting; chats are execution context, not durable project memory.

## Canonical startup

1. Verify that the repository checkout/connected GitHub view is the intended `jderhagopian-stack/fsffl-next` repository and that its main branch is current. Record the exact main SHA. Do not assume a cached or stale local clone is authoritative; reconcile it with GitHub before editing.
2. Read `docs/operations/CURRENT_OPERATIONS.md` for the sole current cross-workstream status and operational source of truth.
3. Read `docs/operations/OPERATING_PROTOCOL.md` for authority, execution, validation, promotion, and handoff rules.
4. Read the governing product/architecture philosophy: `docs/charter.md`, `docs/NORTH_STAR_PRODUCT_DIRECTIVE.md`, `docs/architecture/overview.md`, and `docs/architecture/authority-boundaries.md`. For architecture-recovery work, also read `docs/operations/directives/20261005_ARCHITECTURE_SIMPLIFICATION_AND_DEVELOPMENT_RECOVERY.md`.
5. Read the named active workstream checkpoint under `docs/operations/workstreams/` and each authority or evidence artifact it directly names. Reconcile the request with that checkpoint and current GitHub/Render evidence. Do not restart completed work or treat files under `docs/operations/archive/` as current state.
6. Keep changes within the authorized scope. Preserve ownership/authority boundaries, exact identity and provenance contracts, and explicit acceptance gates. When the durable directive conflicts with a new Management instruction, follow the latest explicit instruction and checkpoint the disposition before broadening work.

## Architecture philosophy

Build governed intelligence once for an exact State, publish it coherently, reuse it cheaply, and let product readers consume it. Keep authority one-directional:

`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Each concept has one authoritative owner. Downstream layers consume rather than recreate upstream truth. Presentation explains governed results; it does not invent or silently alter model conclusions. Prefer small, modular, auditable changes and deterministic tests over duplicated lifecycle/orchestration paths. Escalate validation in proportion to the boundary and blast radius changed.

## Test, merge, and deploy method

- During implementation, run focused tests for the changed contract and regressions. Do not use the full suite as an iterative development loop.
- When the PR is stable and proposed for merge, run the affected focused regressions and exactly one full suite at that stable head. The generic PR CI is the merge gate.
- A changed PR head supersedes prior results; obsolete in-flight CI runs are canceled. The required `CI / test` check remains intact. Never rename, remove, bypass, or weaken required merge checks to reduce test cost.
- Do not repeat the full suite on the merge push. Generic CI runs on pull requests, not the merge push.
- Merge only the reviewed stable head after required checks pass. Record exact PR/head/merge SHAs and validation results. Deploy only when the workstream requires it; verify and record the exact deployed commit and runtime evidence.
- Documentation-only post-deploy checkpoint updates do not require a second full suite unless they change executable behavior or a governing gate.

For every handoff, persist exact repository identity, branch/PR/head, tests, merge/deployment evidence when applicable, unresolved risks, and the next authorized action in the canonical operations/workstream record.
