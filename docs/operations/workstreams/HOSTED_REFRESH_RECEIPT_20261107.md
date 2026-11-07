# Hosted refresh receipt — 2026-11-07

The deployed correction lets core intelligence finish and survive a restart, but does not make the complete Career journey safe on the existing instance. Render confirmed an OOM kill during post-publication work. Do not repeat the refresh or declare Career/Position & Depth accepted.

## Exact execution

- Repository: jderhagopian-stack/fsffl-next. Deployed commit: 02ffb963218d2a1408ecb58b1c07a563e9845054; Render deployment dep-dbnoncu7bikc73d4oc3g.
- Existing single web service: srv-dae6k7vqj5pc73af7bt0, 0.5 CPU, 512 MiB. No worker process, plan/configuration/provider/schema change.
- User initiated one POST /api/intelligence/jobs at 20:48:04 UTC. Agent performed read-only observation.
- Job intelligence:bf580e335a5b42b9a6c06c3694ae6a92: completed, error/failure_phase null, 229.624735921 s. Created 20:48:04.329274; completed 20:51:54.047876 UTC.
- New State: 14f7f85f2a342769050981873a765022ae6e22e58c58b06b97cb2f3d230614b7.
- Presentation generation: 88ae36e6ec33083ddddd01cd3061e0b8d550933500f42801f0261c507d9fc06c.
- Read-only Supabase queries confirmed new Forecast, Simulation, Value, Current Intrinsic, presentation manifest/surfaces, last-good bundles and completed lifecycle records.

## Measurements and incident

| Stage | Observed runtime | Memory evidence |
|---|---:|---|
| Forecast replay discovery | 14.418 s wall / 7.085 s process CPU | Sampled RSS 355,627,008 B |
| Forecast completion | 20:48:36.714 UTC | Process peak 395,575,296 B (377.25 MiB) |
| 50,000-trial simulation kernel, batch 500 | 8.325 s wall / 4.060 s process CPU | Sampled RSS 378,327,040 B; no higher process peak |
| Current Intrinsic reconciliation | lifecycle phase 93.223 s | Process peak 444,051,456 B |
| Attaching/publication | lifecycle phase 83.137 s | Process peak 457,007,104 B (435.84 MiB) |
| Core job total | 229.625 s | Above 429,496,720 B working target; below hard limit at publication |
| Post-publication Career / browser traffic | interrupted 20:55:05 UTC | Last observed RSS 564,867,072 B (538.70 MiB); reported process high-water 563,441,664 B |

RSS and Render charged/container memory are different measurements; do not interpret the RSS value as the exact enforced-container peak. Render 30-second memory samples reached 499,302,400 B at 20:55:00, below its 536,870,900 B limit. Five seconds later event evt-dbnp0ae0tbcc738kua30 at 20:55:05.212622 explicitly reports oomKilled memoryLimit=512Mi. Coarse samples therefore missed the fatal peak. CPU samples reached the complete 0.5 allocation during core work and again before failure.

Product Context requests during the follow-on window took approximately 15–21 s server time. Client telemetry recorded network_error around 26 s and product_context_restore failed, even where the server eventually logged HTTP 200. These are observed client failures, not proof of a platform HTTP timeout threshold.

The instance restarted at 20:55:06, became available at 20:55:25, and at 20:55:51 restored the new exact State with forecast=True, simulation=True, value=True, intrinsic=full. Restore RSS 330,649,600 B, process peak 350,625,792 B. Durable core publication survived. The completed core job did not record the optional Career OOM as its own failure.

## Coverage and completion limits

- Current Intrinsic artifact is ready for 334 players, matching the prior persisted Current population; this is not a claim of full roster Career coverage. Local frozen-335 parity tests and this live 334-player authority are distinct populations.
- No new career_intrinsic_v1, career_intrinsic_reference_checkpoint_v1 or foundation4_long_horizon_y4_y7_shadow artifact was persisted during this run.
- Saved league_team_views Current Position & Depth status is partial: one or more configured lineup slots lack complete governed Current outlook authority.
- Saved Dynasty position rooms are unavailable. No new Career fingerprint is present in the presentation manifest.
- Saved market lenses are degraded (forecast covered 215/257 rostered; 320/874 all). These authority populations must be explained, not silently expanded or reduced.
- The last explicit phase before failure was post-publication active=intrinsic. No Career subphase start/finish marker was emitted before the kill, so the exact allocation/function causing the peak is NOT established. Do not claim the dynamic fit was reached or completed.

## Files and current path

1. src/fsffl/product/static/forecast_refresh.js posts /api/intelligence/jobs and polls current.
2. src/fsffl/product/webapp.py start_intelligence_job/reconcile: State, Forecast, simulation, Value, Current Intrinsic, checkpoint and atomic publication.
3. src/fsffl/product/background_jobs.py: in-process executor, lifecycle persistence and phase timers; completed core does not cover later optional work.
4. src/fsffl/product/persistent_webapp.py: single-process composition; heavy-work coordinator; _reconcile_hosted_intrinsic; _prepare_presentation_for_user starts Career after durable publication; _promote_presentation_for_user composes eight surfaces; Current Position & Depth provider consumes governed forecasts and history.
5. src/fsffl/persistence/session.py: State/team snapshots, derived artifact encoding/writes and atomic manifest/pointer; existing bounded pooled transport remains intact.
6. src/fsffl/product/intrinsic_background.py: separate thread executors still share web-process RSS/CPU. current() computes its compatibility key before inspecting retained records; weak-contract restore is lane guarded.
7. src/fsffl/product/private_beta_shapley_runtime.py: compatibility identity resolves preserved Year-1 evidence and Future contract and builds semantic JSON. Removing request() from GETs does not make key computation allocation-free.
8. src/fsffl/product/foundation4_career_forward_runtime.py and foundation4_shadow_inputs.py: Current + Y4–Y7 + terminal/tail objects coexist while reference is composed; checkpoint then dynamic roster expansion, release and final save.
9. src/fsffl/product/dynamic_career_composition.py: dynamic fingerprint constructs a list of raw forecast tuples plus source/history identities and JSON; expansion delegates to bounded P0 acquisition/materializer.
10. src/fsffl/product/p0_live_candidate_runtime.py, providers/sleeper_snapshot.py and scripts/materialize_foundation4_dynamic_candidates.py: deployed bounded identity/stat retention and slim reference coordinates; remaining historical frames, copies and serialization are potential contributors, not measured OOM attribution.
11. src/fsffl/product/presentation_continuity.py: manifest proof uses metadata/read bundle; do not falsely attribute repeated full presentation payload reads to plain has_snapshot().
12. src/fsffl/memory_attribution.py: existing application phase sampler/high-water reporting; early Career boundaries need equivalent coverage.

## Diagnosis and smallest next proposal

### User-visible Franchise confirmation

The user's subsequent screenshot shows Broad Market and projections present, but both 3-Year and Career Intrinsic unavailable across displayed starters. Read-only inspection confirms this is represented in the saved publication, rather than merely a browser formatting problem: both value-lens surfaces carry `fsffl_intrinsic.status=unavailable`, player_count=0, reason `Matching Career evidence is unavailable for the active publication generation.`

The user clarified these missing values occur throughout the product, not only Franchise. Acceptance must cover every consuming view. The user also reported the Current WR room failed. Follow-up read-only queries confirmed only team 1 had an incomplete optimized WR group (2/3); current_position_depth.py deliberately makes the WR comparison unavailable for all 12 teams if any team cannot fill its configured slots. The saved output was already partial before the Career crash, so do not attribute this failure to that later OOM.

For that team the saved outlook lacks six rostered WRs: Jonathan Mingo (10225), Jalen McMillan (11618), Luke McCaffrey (11650), Jaylin Noel (12536), Tyreek Hill (3321) and Brandon Aiyuk (6803), all under the sleeper:player namespace. The latest projection tables contain only Razzball ROS rows for the first three and none for the other three. This is evidence of source coverage gaps, not proof of each player's exact scorer/roll-forward rejection. build_governed_in_season_outlook returns per-player season_outlook_failures, but build_governed_current_position_depth does not preserve those reasons in its returned/persisted contract. Trace exact admitted sources, minimum-source/scoring rules and roll-forward failures before changing fallback behavior. Do not fabricate forecasts, treat missing values as zero or relax the all-team denominator simply to fill the room.

Main was fetched again at this investigation checkpoint and remains 02ffb963218d2a1408ecb58b1c07a563e9845054. No subsequent executable fix or deployment exists. The broader recipe/dependency/release issues from PROJECT_DELIVERY_REVIEW_20261107.md remain open; findings and proposed work must not be reported as implemented.

`static/my_team_dashboard.js:loadFranchiseNorthStarValueLenses` reads `/api/league/value-lenses`. In `league_value_lens_routes.py:with_career`, user-facing 3-Year rows are derived from the matching Career contract through `build_three_year_intrinsic_player_values`; exact-State/generation validation applies. Thus the ready standalone Current artifact does not satisfy this surface's Career-backed 3-Year requirement. Career failure explains both empty columns. Do not bypass that accepted cohort/publication contract by substituting the standalone 334-player artifact. Core readiness should explicitly distinguish standalone Current readiness from complete user-facing 3-Year/Career coverage. This is an additional concrete acceptance requirement for the proposed fix.

Both code/resource ownership and the service limit matter. The simulation is already bounded and completes quickly. Core alone exceeds the working memory target. Long optional work plus foreground requests share the same 0.5 CPU/512 MiB process, saturate CPU, delay readers and ultimately exhaust the enforced memory limit. Existing heavy-phase serialization is not a process memory boundary and does not encompass every reader allocation.

Proposed next code slice, before any further deployment:
- Bind completed-record lookup to a once-computed exact governed dependency receipt, preserving every semantic/source/rule/model invalidation; avoid rebuilding the full compatibility graph/JSON on routine readers. Deduplicate concurrent receipt resolution. Do not replace exact identity with State-only caching.
- Attribute Career preflight/fingerprint, frozen input loading, Current reuse, long-horizon/tail construction and checkpoint separately; measure retained graphs before/after browser reads with replayable published evidence.
- Reuse validated frozen inputs where identity permits, remove duplicate transient arrays/frames/serialization graphs, release phase inputs and process dynamic candidates in bounded batches. Preserve all outputs, cohorts, snapshots, schema witnesses and accepted source cutoffs.
- Give optional Career its own durable observable status so core-completed cannot imply full capability readiness.
- If that cannot demonstrate safe headroom under the unchanged cap, use the existing fenced job seam as the starting point for an isolated refresh process/worker, with one owned job, atomic publication and last-good. Merely moving work to another thread will not fix RSS. Separate worker/queue infrastructure is a subsequent concrete proposal, not deployed or presumed authorized.

No further executable changes, redeploy or retry were made after this failure. The prior deployment record PR #516 is green but automatic approval review rejected its manual merge as an unapproved default-branch mutation; no workaround was attempted. This receipt and canonical status overlay are local pending review.

## Subsequent authorized correction — implementation in progress

The user explicitly requested fixes after clarifying that Intrinsic was missing throughout the app and the Current WR room also failed. Main fetched again at `02ffb963218d2a1408ecb58b1c07a563e9845054`. Implementation branch `fix/refresh-resource-coverage-20261107` carries the incident documentation and a bounded correction; nothing from this correction is deployed.

### Confirmed redundant reference calculation

Private read-only copies of the failed State, ready Current contract and the previously persisted Y4-Y7 component are now available in temporary local files (never commit them). The new State's exact aligned Y4-Y7 fingerprint is **d3d95c6490750d13596bc576842a673ba3d85b4f94c11edae3ba3fb459dc7df4**, identical to the existing October 28 component, with the same 334-player cohort. The Career build nevertheless recomputed that component instead of taking the exact-key durable restore path already used by explicit component readers.

The correction tries that exact component restore during Career construction, validates the decoded fingerprint/model/cohort, and falls back to the unchanged calculation on absence or invalidity. A reused component is not encoded/written again; the new Career reference/expanded contracts still receive their normal exact-State checkpoint/publication. Source cutoffs, cohort membership, permutations, arithmetic and model versions are unchanged. Add early frozen-input/Current-reuse/component-restore/build attribution so a future kill has a subphase entry marker.

Local replay of the unchanged 334-player reference calculation took **77.480 s**, peak **211,144 KiB**. The corrected loader using the matching persisted component took **0.835 s**, peak **195,660 KiB**, and its complete 334-player reference output matched (including production residual disclosures). This is the reference portion using real saved State/Current/component, **not** the full dynamic-roster refresh or hosted headroom acceptance. NumPy/Python environment differences from Render remain relevant. No database write occurred; replay uses an isolated read-only fake store and discards proposed writes.

Concurrent exact-input compatibility checks now share only an in-flight result. This avoids duplicate scoring/semantic-JSON graphs during overlapping product reads without introducing a TTL, State-only memoization, or stale source identity cache. Different immutable State/Forecast objects, user, pinned cutoff or cache epoch do not share. Later non-overlapping calls recheck producer authority. The core completion message now explicitly distinguishes core publication from Career/user-facing 3-Year/Dynasty readiness.

### WR replay and remaining evidence gate

Saved canonical ROS revisions **CBS snapshot 168 (2,160 observations)** and **Razzball snapshot 169 (2,490 observations)** were replayed locally through the unchanged in-season Forecast runtime, at the saved November 7 cutoff/window. Mingo, McMillan and McCaffrey each have only Razzball observations, no admitted ensemble metrics and no strict-scorer partial. Noel, Hill and Aiyuk have no provider observations. Therefore the existing scoring-gap-only preseason fallback is not eligible, and the accepted two-source rule cannot fill team 1's third WR slot. The code correctly withholds a league-relative WR denominator for all teams; this is independent of the later Career OOM.

Current Position & Depth now carries each player's existing Forecast rejection reason and the incomplete team IDs in its published contract, rather than dropping them at composition. This fixes diagnostic plumbing, not missing numerical coverage. Tests preserve unavailable ranks and prevent zero imputation. Additional admissible provider evidence or an explicitly reviewed new fallback is still required for full WR-room acceptance; no source rule was relaxed.

Direct CBS HTML fetch is blocked by the execution network proxy (403); the connected web reader confirmed the existing ROS page but exposed no pagination evidence. A speculative `?page=2` request was inaccessible. Do not implement guessed pagination or claim the missing CBS subjects were recovered. Fresh web output is not substituted for the saved replay inputs.

### Candidate validation

- Final compatibility/dependency/Current selection: **25 passed**, 35 deselected, 3.15 s. Includes concurrent exact-input sharing, non-overlapping freshness rechecks, distinct State/Forecast/epoch/cutoff separation and dependency invalidation.
- Career component/checkpoint/restore selection: **9 passed**, 41 deselected, 164.04 s. Includes unchanged full reference composition, exact-component reuse, corrupt payload rejection, durable restart and checkpoint persistence guards. A final assertion that reused components are not rewritten is also included in CI.
- Presentation/refresh/league-value consumers: **43 passed**, 3.10 s.
- Final Current and core refresh-resilience selection after diagnostic/completion wording changes: **11 passed**, 2.78 s.
- Selections overlap. One initial broad run was stopped after a shared-fixture contamination failure in a new test (85 passed, one failed); the new tests now decode their own component rather than mutating the module-scoped loader cache. The corrected selected tests pass. Do not describe that interrupted run as a passed suite.
- `git diff --check` passes. Private saved input/output files remain outside the repository with mode 0600. Remote CI, exact-head Stable/review, full dynamic/hosted memory and all-view physical acceptance remain required before promotion.

No claim that the WR room is numerically restored or that the deployed service is fixed. The proposed source/fallback decision remains explicit; there is no model-rule change in this candidate.
