# Engineering Automation Bootstrap — Issue #456

**Authority:** [Issue #456](https://github.com/jderhagopian-stack/fsffl-next/issues/456), existing [Operating Protocol](../OPERATING_PROTOCOL.md), and [Worker Bootstrap](../../../AGENTS.md).
**Status:** BOOTSTRAP IN PROGRESS, not complete; **no agent is yet installed or working unattended**.
**Owner:** a single isolated automation workstream. Existing Career #405/#454 implementation is unchanged.

## Why this is needed
As of 2026-10-13, GitHub Actions runs successfully on other branches, but no Actions run is associated with the latest Career #454 head. The `main` branch API reports unprotected status and no required status checks. The cause of missing Career event-triggered CI is not yet established. The canonical `CURRENT_OPERATIONS.md` was behind newer Career instructions and release authority.

This workstream restores **enforced execution**, not a new AI management philosophy. Repo-first Management remains the decision authority; agent sessions must not reinterpret accepted Charter, Forecast/Simulation/Value, State or publication contracts.

## Accepted scope and sequence
1. Reconcile the canonical current-state record with verified Career, GitHub and Render status; preserve all historical sections for traceability.
2. Prove a native GitHub event starts a read-only GitHub Actions workflow on the exact commit. The isolated `.github/workflows/automation-bootstrap-smoke.yml` is **only this trigger/checkout test**, not a coding-agent integration, and cannot claim acceptance without a real Actions run URL.
3. Investigate missing CI specifically at GitHub event/token/permissions boundary. Do not relax existing tests or assume ordinary API-driven changes must produce a run. Establish a tested, authenticated way to trigger/check exact-head CI.
4. Configure `main` branch protection or a ruleset with the *observed*, stable successful check names. This requires authorized GitHub repository administration, which the present connector does not expose; do not falsely claim checks are enforced.
5. Integrate a **supported, compiled** GitHub Agentic Workflow using an already eligible AI engine (Codex if its separately billed API credential is approved). Install with the official `gh-aw` tool; never hand-author an uncompiled/inert agent workflow and claim it works. Store any necessary credential as a GitHub Actions secret via owner-authenticated UI/CLI, not in Git, logs, issues or chats. Start with read-only issue triage; add safe-output code-write permission only after explicit validation.
6. Controlled pilot: a trusted maintainer-only label launches one agent on a harmless issue; it opens a draft test PR; CI runs on the exact head; one purposefully failed isolated test is repaired in **at most two** bounded attempts with a durable retry counter and no overlapping writers. Stop on any authority, cost, security or deployment ambiguity. No merges/deploys during pilot.
7. Record real event, CI, repair, retry, commit and cost evidence in this file. Issue #456 closes only when the end-to-end unattended exercise completes without a human poke.

## Security and resource boundaries
- No Career #454 edit, source-data acquisition, provider or database write, Render deployment, billing change or infrastructure purchase.
- No automatic merge or deployment and no disclosure of private Sleeper/player artifacts in a public repository.
- Least privilege: read-only GitHub token in validation jobs; separately scoped write operations; no untrusted source execution in privileged workflow context; maintain tenant safety.
- Preserve current release protocol and proportionate validation. An agent's text summary is **not proof** of a workflow run.
- Use the current accepted main snapshot only, reconcile against GitHub before any additional change; do not modify unrelated draft PRs.

## Verified bootstrap facts (2026-10-13 ET)
- `main` verified SHA `2bb53f96a7e45283552b348fffad9c3635fbd913`; GitHub `protected=false`; no visible rulesets/required checks.
- Career PR #454 verified open draft, head `36fc608405795ac5fd0b2d32d1f21479f5192cf7`; focused local tests previously 164 passing; full Week 5 Career 243/252 values and nine explicit unresolved; peak full-path RSS 536.676 MiB vs 429,496,720-byte gate; current-head GitHub Actions missing.
- The latest live Render deploy is still `2f89e83edbfbf31f72157735ced5fff4b0c4de5c` on the 512 MiB plan; Career not in production.
- Existing GitHub Actions does run on other PRs; the repository has a standard `CI` and a draft-gated `Stable full suite` workflow.
- A GitHub Codex PR **review** integration has been observed. This does not mean an autonomous *coding/repair dispatcher* is installed.

## Remaining acceptance records
- [ ] Exact-head smoke run URL and event proof
- [ ] Concrete root cause for missing #454 Actions and corrected reliable trigger with observed run
- [ ] Protected `main` with required passing CI check(s), verified by effective GitHub settings
- [ ] Compiled and authenticated issue-triggered coding workflow, least privilege
- [ ] Trusted-label-to-draft-PR run URL
- [ ] Failed test to bounded automated repair and final exact-head CI success, with run URLs
- [ ] Duplicate-event / retries / permissions denial handling checked
- [ ] Close issue only after user-independent proof; no production changes
