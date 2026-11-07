# Project delivery and code review — 2026-11-07

## Scope and authority

User requested continued refresh diagnosis plus a broader code/inconsistency review and a practical route to finish capability deployment and resume the roadmap. This report is a bounded review, not a full security or every-file audit. It proposes sequencing; it does not promote historical models, authorize spending, apply migrations, or declare hosted capability acceptance. No external writes, merge, push, deployment, provider acquisition, or production data changes were performed.

Repository: `jderhagopian-stack/fsffl-next`. GitHub main fetched and verified at `1c757c99d4a54a59d36991f5121d2c949b555f42`. Review checkout: `/workspace/fsffl-review`. Local memory-candidate checkout: `/workspace/fsffl-memory-review`, based on PR #489 exact head `d50c84e6cb176da6c4b703bd5300d10cfea4e1ed`, with an uncommitted correction and regression described below. PR #492 reviewed at `2d600af12889aaad4f57e08ab8639ab116f151bc`.

## Executive finding

Preserve accepted Forecast/Simulation/Value/Decision owners. The principal delivery problem is the incomplete runtime/release boundary around those owners, coupled with stale operational summaries and unfinished evidence gates. Main is ahead of production chiefly through dormant historical backend work. Deploying it does not include the pending memory correction or introduce a worker. A rewrite, storage migration, provider replacement, and model recreation are not justified by this review.

## Newly verified live facts

Read-only Render discovery in workspace `tea-dae6if9t0dsc73918us0` confirms one FSFFL web service, `srv-dae6k7vqj5pc73af7bt0`, plan `0.5c-512mb`, auto-deploy off, Uvicorn startup. No FSFFL worker was listed. Latest live deployment is `dep-dbk1lni9lscs73fk2khg`, November 2, on `6d1259e1f5f55078398814a6c2383f7a0d544b84`. October 28 deployment `dep-dbgm32rvvlss73b2gs2g` is now deactivated.

Render events explicitly record OOM kills at October 25 03:57:16.816180Z and October 28 15:09:24.793846Z, each with `memoryLimit=512Mi`. The latter is later than the deployed P0-release correction. Thus the earlier report's statement that post-correction full-run evidence was merely missing is incomplete: a later failure is verified.

October 28 14:50–15:12Z metrics requested at 30-second resolution, CPU aggregation MAX: sampled memory maximum 507,097,100 B at 15:08Z; sampled CPU maximum 0.29093465 CPU at 15:09:30Z; limits 536,870,900 B and 0.5 CPU. The sampled memory maximum does not capture the fatal instantaneous peak. This window does not prove CPU saturation. Historical Foundation4 CPU/wall evidence remains separate. Application logs returned no entries for the queried incident window; absence of retained logs is not absence of failure.

## Findings, ordered for delivery

### P1 — Pending memory PR can still reject a valid saved roster

PR #489 `p0_live_candidate_runtime.py:1009–1038` passes only `exact_state_rostered_p0_subject_ids()` to bounded catalog enrichment. That helper excludes frozen reference players. The following validation checks **every** saved-roster player. A frozen-reference player subsequently dropped from live rosters disappears from the bounded current identity universe despite still being present in the provider catalog; the whole build can fail.

Reproduced with real normalizer logic: full normalization retains the dropped identity; candidate normalization omits it. Added a builder-boundary regression using an actual frozen source ID; it fails against the original candidate and passes after the local correction. The correction retains fresh identity/status for all exact-State roster IDs, while keeping scoring/stat work restricted to dynamic P0 IDs and excluding unrelated waiver identities. This is bounded by roster size and does not change source rules or model math. Local change is not pushed and is not production memory acceptance.

PR #489 is open, non-draft, mergeable, with successful exact-head CI `40682778523` and Stable `40682778547`. Its one listed review thread remains unresolved; its earlier partial fix does not cover the frozen-reference case above. Any new pushed correction must follow the draft/development/exact-head gate again. Green old-head CI is not clearance for the new local change.

### P1 — Reader routes can still enqueue upstream computation

`shapley_intrinsic_routes.py:54` and `player_intelligence_routes.py:298` call `intrinsic_coordinator.request()` from GET handlers. `intrinsic_background.py:447` submits work on a cache miss. Therefore a nominal product read can initiate heavy Current computation. The shared gate limits overlap, but does not make this a cheap read or isolate its failure from web availability. Career GETs have already moved toward `current()`-only consumption, so the remaining routes are inconsistent with that boundary.

Small correction: use completed/guardedly restorable evidence on GET; return truthful loading/refresh-required status if absent. Let explicit connect/refresh own scheduling. Test cold read, durable restore, active Career weak-release, and no new submit. Do not simply remove durable restoration or turn transient release into permanent unavailability.

### P1 — Production computation has no independent failure boundary

`background_jobs.py`, `intrinsic_background.py`, and `foundation4_dynamic_candidate_runtime.py:118` execute refresh/model work in the web process. Serial admission and GC cannot guarantee survival when one stage or serialization exceeds the remaining memory. Current main still has this design.

PR #492 has deterministic job references, fenced leases, bounded retries and pooled PostgreSQL ownership. It is draft and GitHub reports it nonmergeable. It has no active worker daemon/model execution integration, unapplied queue schema, and no cutover. It is enabling code, not a deployable fix. Reconcile it with main, complete the existing boundary rather than introducing a competing queue, then prove the full accepted model path and crash/last-good behavior privately. A subprocess in the same memory-limited container is not independent capacity.

### P2 — Deployment recipe does not reproduce the running contract

`render.yaml:14` asks for `FSFFL_BETA_PASSWORD`, while `webapp.py:149` requires `FSFFL_BETA_PASSWORD_SHA256` when auth is enabled. A new service created strictly from the recipe would lack the credential variable the code reads. This does not establish a live authentication outage.

The recipe also names a different service/plan and `/health`; live Render shows the existing paid-size plan and an empty HTTP health-check path. Treat the recipe as drifted, not a faithful infrastructure source. Reconcile documentation/configuration deliberately; do not apply the Blueprint or change the live health configuration during this review.

### P2 — Replay/release reproducibility has contradictory dependency contracts

`pyproject.toml:16` requires pandas `<3`; both `career-coverage-pr1-parity.yml:40` and `career-coverage-pr1-semantic.yml:29` request editable current code plus pandas `3.0.6` in one pip invocation. Those requirements conflict. These legacy recovery workflows are branch/manual tools, not proof the normal CI is broken.

Main CI and Stable use Python 3.11, while runtime-sensitive hosted and history evidence includes Python 3.12.10. NumPy identity is guarded, but most other numerical/web dependencies remain broad ranges. Preserve original accepted replay environments separately; do not rewrite their historical numerics merely to satisfy today's package constraints. Add a current executable runtime manifest and a targeted hosted-runtime gate for runtime-sensitive changes, keeping the ordinary focused/full-suite process proportionate.

### P2 — Operational truth is fragmented

`CURRENT_OPERATIONS.md` contains a dated “current” recovery subsection with a deactivated deploy and many older next-action gates. `PRODUCT_ROADMAP.md` includes old “next” items for already completed Simulation/navigation work. Open PRs include old research and overlapping documentation/implementation lanes. These are not all unshipped product features.

Maintain one short capability/release matrix with separate columns for research accepted, merged, deployed, real-data acceptance, and physical acceptance. Preserve chronology below it. Reconcile/close stale PRs only after verifying their changes and evidence were absorbed; no blanket merge/closure.

### P2 — Historical backend completeness and product completeness differ

PRs #513/#514 are merged. `historical_roster_replay.py` supports normalized player/pick/budget reversal; `historical_roster_state.py` reuses one State materialization validation path. The code correctly keeps retrospective State ineligible for a PIT Decision grade. Synthetic materialization succeeds with sufficient receipts. The real 2023 archive still lacks independent placements, complete pick/balance coverage and eligible at-time analytical evidence.

Next deliverable should be a machine-readable real-archive coverage/blocker report at selected cutoffs, not another general historical framework or a premature trade-grading UI. Keep fantasy league history and NFL/player/model evaluation data inventories separate. Fact-only records may use adequate factual evidence without waiting for historical valuation; grades require their own missing Forecast/Value/Decision authority.

### Public launch limit — variable league size is not universal product support

Canonical positions and model capabilities remain bounded; scoring code explicitly reports unsupported/partial rules. Current beta authentication is one configured Basic Auth identity. Varying synthetic team counts proves mechanics, not IDP, auction/salary formats, public accounts, entitlements, or tenant security. Preserve these as explicit launch gates rather than using “league agnostic” as an accepted universal claim. No new security vulnerability or live cross-tenant leak was established here.

## Validation and limits

- Current main historical coverage/replay/State/materializer/lineage/audit selection: **85 passed**, 1.11s.
- Current main Forecast scoring, Market discovery funnel and bilateral Trade Decision selection: **30 passed**, 3.38s.
- Current main browser/resource-boundary selection: **27 passed**, 14.92s. Fresh browser subprocess separately reported **185,569,280 B (176.97 MiB)** peak and one passing acceptance case. This uses mocked model outputs, not a full Career fit.
- PR #489 original selected tests: **46 passed**, 3.35s. With local roster correction/regression: **47 passed**, 3.37s. New regression demonstrably fails with original identity selection. `git diff --check` passes.
- Prior refresh review's local 50k synthetic PCG64/batch-500 kernel measurement: 1.386s wall, 1.538s CPU, 52,400,128 B peak; not full refresh or hosted runtime acceptance.
- Earlier browser timeout was reproduced with a trivial FastAPI TestClient under restricted execution. Granting network permission made the trivial request and actual browser/resource tests pass. It is an environment restriction, not a demonstrated application timeout.
- No full suite repeated for this audit/local unstable patch. No private accepted State/source-response checkpoint is mounted, so no current-input full Career replay, exact numerical parity claim, or real full-refresh peak is available.
- Live Render inventory/deploy/event/metrics were queried; no authenticated production browser journey or live database inventory was performed.

## Proposed execution order

1. **Finish one beta reliability release.** Carry the local saved-roster fix into the existing memory candidate, add read-only route scheduling regressions/correction in a separately bounded change, reconcile deploy recipe/runtime dependencies. Validate exact heads and the preserved full workload privately; measure serialized write and presentation phases, not only fitting. Preserve last-good and all player/exception/source identities. No repeated production trial-and-error.
2. **Complete the independent worker proof when combined-path evidence requires it.** Reuse #492; independently run real Career with existing owners, one bounded job, finite lease/retry, current-State result fencing and existing atomic publication. Test crash, stale completion, restart and fallback. Choose actual capacity/cost only after worker and web measurements; do not equate fault containment with reduced total resource cost.
3. **Keep the independent historical foundation lane moving.** Run one retained-season coverage report through the merged replay/State bridge; acquire or explicitly disposition exact missing facts. Avoid adding helpers indefinitely without an executable end-to-end data deliverable.
4. **Finish a useful current product slice.** Once beta reads/builds are reliable, validate Explore → one candidate → bilateral Trade result on a real published State. Reuse staged cheap Search and targeted Simulation. Separate consumer readiness from core readiness; keep market, raw Intrinsic and team utility meanings distinct.
5. **Extend shared intelligence in dependency order.** Versioned historical/forward model evaluation panel → eligible historical/realized comparisons → evidence-backed Owner/Decision uncertainty → Record Book/league memory and deeper What-If/Multiverse. Fact-only records can ship earlier where their factual coverage is independently sufficient.
6. **Commercial readiness as a measured track.** Explicit supported-format matrix, account/tenant isolation, provider agreements before launch, quotas/rate limiting, backup/restore, queue throughput and cost per refresh. Preserve accepted pooled persistence; optimize measured duplicate acquisition/bytes before selecting any storage migration.

Each release needs an exact source/runtime identity, focused evidence for its changed contract, exact-head Stable gate when merge-ready, targeted hosted check for runtime-only behavior, and physical acceptance only for the affected customer journey. Do not reopen accepted unrelated models or use one blocked capability to freeze independent backend work.

## Next authorized action and handoff

Local review and first narrow candidate correction are complete. Resume from PR #489 head and the local diff; do not overwrite it or merge old green-head evidence. No deployment or public PR write has occurred. The immediate remaining measurement blocker is privately mounted accepted State/provider-response inputs. Review the GET scheduling change as the next separate code slice. A provider/plan/storage change is not required to review or prepare either correction.
