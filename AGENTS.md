# Worker Bootstrap

This file is the repository-root entry point for every worker, including Management successors. Begin here before acting; chats are execution context, not durable project memory.

## Canonical startup

1. Verify that the repository checkout/connected GitHub view is the intended `jderhagopian-stack/fsffl-next` repository and that its main branch is current. Record the exact main SHA. Do not assume a cached or stale local clone is authoritative; reconcile it with GitHub before editing.
2. Read `docs/operations/CURRENT_OPERATIONS.md` for the sole current cross-workstream status and operational source of truth.
3. Read `docs/operations/OPERATING_PROTOCOL.md` for authority, execution, validation, promotion, and handoff rules.
4. Read the governing product/architecture philosophy: `docs/charter.md`, `docs/NORTH_STAR_PRODUCT_DIRECTIVE.md`, `docs/architecture/overview.md`, and `docs/architecture/authority-boundaries.md`. For architecture-recovery work, also read `docs/operations/directives/20261005_ARCHITECTURE_SIMPLIFICATION_AND_DEVELOPMENT_RECOVERY.md`.
5. Read the named active workstream checkpoint under `docs/operations/workstreams/` and each authority or evidence artifact it directly names. Reconcile the request with that checkpoint and current GitHub/Render evidence. Do not restart completed work or treat files under `docs/operations/archive/` as current state.
6. Keep changes within the authorized scope. Preserve ownership/authority boundaries, exact identity and provenance contracts, and explicit acceptance gates. When the durable directive conflicts with a new Management instruction, follow the latest explicit instruction and checkpoint the disposition before broadening work.
7. For any conclusion that an accepted model/method is missing, obsolete, static, or must be recreated, trace the claim back through the original governing research/production decision, exact accepted code/workflow/artifact identities, and current runtime contract before acting. Absence of a serialized runtime object is not evidence that the methodology was lost. If a later workstream summary appears to conflict with the charter or original accepted authority, stop and reconcile the contradiction at the earliest authoritative layer rather than reinventing the concept.

## Architecture philosophy

Build governed intelligence once for an exact State, publish it coherently, reuse it cheaply, and let product readers consume it. Keep authority one-directional:

`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Each concept has one authoritative owner. Downstream layers consume rather than recreate upstream truth. Presentation explains governed results; it does not invent or silently alter model conclusions. Prefer small, modular, auditable changes and deterministic tests over duplicated lifecycle/orchestration paths. Escalate validation in proportion to the boundary and blast radius changed.

Design every capability for multi-league reuse by construction. Before introducing expensive work or a cache/persistence key, identify its widest safe semantic dependency scope instead of defaulting to league/user ID. Shared provider/model/rules work should be reused across leagues when mathematically valid; tenant-private State remains isolated. Do not require brute-force 1,000/10,000-league tests in the constrained beta environment: validate with measured unit costs, bounded synthetic tests, reuse/cardinality assertions, and explicit scale projections unless larger execution is specifically justified and resource-safe.

## Test, merge, and deploy method

- During implementation, run focused tests for the changed contract and regressions. Keep implementation PRs in draft while making code/checkpoint pushes; generic `CI` runs focused Dynasty readiness regressions only and cancels superseded in-flight runs.
- When the exact PR head is stable and proposed for merge, mark the PR ready for review. `.github/workflows/stable-full-suite.yml` runs the full suite for a non-draft PR on open/reopen/ready/synchronize events. It checks out the event's exact head SHA and verifies that the PR head still equals that SHA before and after the suite.
- If more development is needed after a stable run, return the PR to draft before pushing. When ready again, marking it ready runs the full suite on the new head. Before merge, confirm the latest PR head SHA exactly matches a successful `Stable full suite / full-suite` run. Do not repeat the suite for ordinary draft checkpoint pushes.
- Do not repeat the full suite on the merge push. Generic CI runs focused tests on pull requests; the stable full-suite workflow runs only for a non-draft merge candidate.
- Keep the existing `CI / test` check name unchanged. Do not claim a workflow is a GitHub-enforced required check unless authorized branch-protection/ruleset settings confirm it. If settings cannot be inspected, treat the successful stable-head run as a procedural pre-merge gate and record that enforcement is unverified.
- Merge only the reviewed stable head after focused validation and the stable-head full-suite gate pass. Record exact PR/head/merge SHAs and validation results. Deploy only when the workstream requires it; verify and record the exact deployed commit and runtime evidence.
- Documentation-only post-deploy checkpoint updates do not require a second full suite unless they change executable behavior or a governing gate.

For every handoff, persist exact repository identity, branch/PR/head, tests, merge/deployment evidence when applicable, unresolved risks, and the next authorized action in the canonical operations/workstream record.
