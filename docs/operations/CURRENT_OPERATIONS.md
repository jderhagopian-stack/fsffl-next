# Current Operations

Updated: 2026-10-07  
Authority: sole current cross-workstream status. Historical snapshots are under `docs/operations/archive/`. Detailed P0 decisions and evidence remain in [Architecture Recovery](workstreams/ARCHITECTURE_RECOVERY.md).

## Current program

- **Current Position & Depth correction:** **DIRECTIVE COMPLETE.** Management accepted authenticated iPhone/Safari physical evidence for live #415. Final accepted identity remains head `992617723ff5beaa161160f96aa133b25f9afbd1`, Stable full suite `37663748208` (**2,229 passed / 1 warning**), merge `a55a592585050d866425f3601ab3da9e3812c393`, Render deploy `dep-db38ksk9v7es73balsjg`. Compact sticky Franchise, equalized position columns, centered headers, grid-only `SF`, one-row horizontal scrolling and accepted Current/Dynasty semantics are physically accepted. No redeploy is required for this documentation closeout.
- **Franchise Overview consolidation:** FINAL REVIEW CORRECTIVE under [Franchise Overview Consolidation](workstreams/FRANCHISE_OVERVIEW_CONSOLIDATION.md). Exact head `a746e577e2813acd71bb689f4e787843e2186964` passed Stable full suite `37685510399`, but final review on that same head proved two merge blockers: accepted `stale_last_good` Franchise pairs are rejected because served State is incorrectly required to equal target State, and a transient `/api/league/team-views` failure suppresses otherwise healthy Roster / Assets & Picks. PR #418 is back in draft for these two narrow presentation fixes only; then focused Franchise validation and one fresh exact-head Stable full-suite gate.
- **P0.1–P0.4:** complete; do not reopen.
- **P0.5:** lifecycle simplification architecturally complete. Final saved-session iPhone/Safari acceptance found a separate Career Intrinsic coverage blocker: the exact State/publication Dynasty surface was served correctly, while accepted #370 logic withheld ranks because rostered players were absent from the 335-estimate artifact.
- **Dynasty truth correction:** this tranche reports explicit rank readiness and incomplete Career coverage. Global core-intelligence readiness is unchanged. No imputation and no #370 change.
- **Career coverage follow-up:** [Issue #405](https://github.com/jderhagopian-stack/fsffl-next/issues/405), outside Architecture Recovery. The read-only audit verified **25** distinct missing rostered IDs in the exact preserved State (QB 8/12, RB 7/12, WR 4/12, TE 10/12); “22” was a summary-count error. Management has approved the coverage principle. [Career Coverage Extension checkpoint](workstreams/CAREER_COVERAGE_EXTENSION.md) contains the exact boundary trace, extension contract, evidence tiers, on-demand free-agent semantics, limitations and bounded PR sequence. PR1 stopped before code: retained Y4–Y7 evidence has predictions and residual bands but no inference scorer/model objects, and reproducing candidate scores would call the accepted fitting routine. Do not fit or begin PR2 without Management disposition. Exact artifact IDs, hashes, archive contents and expiry dates are in the checkpoint.
- **P0.6:** operational simplification is implemented, merged and deployed: one current-status source, stale status snapshots archived, explicit merge/deploy verification, and five authoritative E2E journeys. Closeout adds the root `AGENTS.md` bootstrap and the final draft-development / ready-for-review full-suite mechanism below. No product/runtime scope is reopened.

- **P0.6 closeout record:** PR #407 merged as `f58872782aa08a38b816517f2c9465439bda4820` from stable head `cdfd88ddc25c86a26069cc56a41e0cddac62fea2`. PR CI run `37556542579` passed focused Dynasty readiness regressions and the one stable-head full suite (**2,197 passed, 1 warning**). This was process/docs/CI-only; no Render deployment was required. Root `AGENTS.md` contains the exact worker startup, architecture philosophy, and test/merge/deploy method.

- **Final CI methodology correction:** PR #409 merged as `b18195e1ddcc84d321cdf4379dd956279ac9037e` from stable head `c08951991b98781755e8eb9e86174386e556aa76`. Draft-head focused CI run `37558978884` passed. After marking ready, stable full-suite run `37559055898` passed its pre/post exact-head checks and **2,197 tests (1 warning)**. Its first attempt (`37558882264`) failed before pytest because the reserved `GITHUB_SHA` resolved to the synthetic PR merge commit; the workflow now uses `EXPECTED_HEAD_SHA`. No suite executed in that failed attempt. The repository rulesets query returned no rulesets; branch-protection reads returned 403, so required-check enforcement remains unverified and is not claimed. No Render deployment was needed.

## Operational source

Read this page for current cross-workstream status and Architecture Recovery for P0 decisions, exact evidence and tranche history. Former CURRENT_STATE, ACTIVE_WORKSTREAMS, ACCEPTANCE_GATES, MANAGEMENT_CONTINUITY, MANAGEMENT_HANDOFF and workstreams/IMPLEMENTATION contents are archived under `archive/`; old status is historical.

GitHub main at P0.6 tranche start: `65fbf0b272f1f856df1424116050d6c7f4e44f6d`. PR #406 merged at `48d6f0941d425d10a63410b3e799ea8daad0607c`; Render service `srv-dae6k7vqj5pc73af7bt0` was verified live on that exact commit at deployment `dep-db2mq5id0e5s73bmnfog` (completed `2026-10-06T21:52:01.856Z`). Startup restore `62c6d182-f6dd-47c0-a8f7-02afbd5e7c2f` reached durable-context ready in `8,096.79 ms`; startup completed without error-level logs.

## Test, merge, deploy

- Focused tests during development; keep implementation PRs in draft for code and checkpoint pushes. `.github/workflows/ci.yml` runs focused Dynasty readiness regressions only and cancels superseded focused runs.
- At the exact stable merge candidate, mark the PR ready for review. `.github/workflows/stable-full-suite.yml` runs the one full suite for a non-draft PR and verifies its SHA matches the PR head before and after testing.
- If more development is needed, return the PR to draft before pushing. Mark ready again only when the new head is stable; this starts a full-suite gate for that new candidate. Before merge, compare the current PR head SHA with the latest successful `Stable full suite / full-suite` run. Do not rerun the full suite for ordinary draft checkpoint pushes or on the merge push.
- Keep the existing `CI / test` job name. **GitHub enforcement is unverified:** on 2026-10-07, the repository rulesets endpoint returned an empty list, but the branch-protection endpoint returned 403 to the connected integration. Do not claim that either CI check is configured as required; treat the exact-head full-suite result as a procedural pre-merge gate until authorized settings can confirm enforcement.
- Render auto-deploy is disabled. Trigger deploy after merge, verify the exact merged commit is live, record deploy ID/completion/startup evidence.
- Documentation-only post-deploy updates need no second full suite.

## Authoritative E2E journeys

Keep the set small and rerun the journey whose boundary changed:

1. **Clean first run and managed-team prerequisite:** new tenant connects/selects league and team, sees explicit prerequisites, reaches first useful publication without cross-tenant data.
2. **Saved-session restore and restart:** existing tenant returns after restart; exact State/team/generation and same-league last-good survive without unnecessary heavy rebuild.
3. **Publication freshness and league switching:** same-State republish refreshes visible generation; FSFFL → Hodor → FSFFL never renders another league's artifact or stale generation.
4. **Hosted tenant isolation:** repeat league switches under hosted sessions and verify tenant-scoped manifests, surfaces and last-good.
5. **Final physical iPhone/Safari acceptance:** after simplification completes/deploys, replay saved-session Position & Depth → Dynasty → Rank; confirm valid ranks when complete and explicit incomplete-coverage messaging when fail-closed. Preserve Current, approved Dynasty, Career Intrinsic, Foundation 4 economics and Simulation 2.0 semantics.

The saved-session physical journey remains pending; exact evidence is in Architecture Recovery. Other workstreams remain governed by their named checkpoint and Management gate.
