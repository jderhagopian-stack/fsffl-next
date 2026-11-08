# Refresh correction acceptance — 2026-11-08

Continuation of the authorized fixes. This is a local post-candidate receipt; it does not change PR #517's stable head or claim complete capability acceptance.

## Candidate identity and review

- Main verified at `02ffb963218d2a1408ecb58b1c07a563e9845054` before promotion.
- PR #517 final head `2841872f782420cb1ee6748c8a2aa394c867b411` (implementation `c84e5c0f8923325359e70edb2eea61a06a4a53e3`).
- Exact-head CI `42441913843`, Home `42441913883`, Atlas `42441913820`, PR164 `42441913822`, Forecast `42441913930`, Intrinsic `42441913833`: success.
- Automated review returned +1 at 03:17:07 UTC on the unchanged final head; no review threads were present.
- Stable full suite `42441934203`, job `128612808236`: **success, 2,667 passed / 5 skipped / one warning in 750.46 s**, exact-head checks before and after passed. No repeat suite on the merge push.
- PR #517 merged as squash `259c7b9e28b157577d3782b6ee77fa2c249d5277` at 03:29:17 UTC. Tested head and merge have identical tree `32a6af6ddd4ebf104a79aa67816b83cfbd8047e5`.
- Existing Render service (one 0.5 CPU / 512 MiB instance, main, auto-deploy off) deployed `dep-dbnupbh5efls73cdm2j0` on that exact merge: **live 03:31:23.208615 UTC**, successful deploy-ended event `evt-dbnuq2oqr7gs73aj0u9g`. No service configuration, plan, provider or schema change.
- Restore at 03:31:36 UTC recovered the November 7 State with Forecast/Simulation/Value and standalone Current Intrinsic ready. RSS **342,052,864 B**, process peak **354,840,576 B**, working budget **429,496,720 B**, active heavy work none, waiters zero. No new failure/restart event at verification. These startup readings do not prove full-refresh headroom or Career readiness.
- The assistant requested one authenticated explicit refresh from the user's signed-in session after live verification. No agent-initiated refresh, production data change or retry occurred. Await that action before claiming hosted refresh/Career acceptance.

## Additional saved-input reader replay

Saved November 7 State, preserved preseason baseline, and exact-State first-party fumbles supplement were decoded privately. Both reader arms use the unchanged production Year-1 scorer and vNext Future provider, a warm provider-semantic Future cache, four concurrent readers, and no provider/production writes. Source acquisition/transport is excluded from this replay.

| Arm | Authority replays for 4 readers | Wall time | Process peak |
|---|---:|---:|---:|
| Original independent compatibility resolver | 4 | 0.646 s | 194,016 KiB |
| Candidate in-flight coalescing | 1 | 0.226 s | 180,244 KiB |

All reader outputs equal fingerprint `431c56ef5443084de599e3e9cc6e06dcc8f7ff4d47ebcfeea5c4453a0753e929`, independently confirmed by read-only SQL as the November 7 production Current Intrinsic artifact key. This proves dependency/output identity for these saved inputs and reduced concurrent replay allocations, not full web/Career headroom.

The earlier 334-player reference replay also remains valid: same full reference output, ~77.480 s recalculation versus ~0.835 s exact persisted-component reuse. It excludes dynamic roster expansion.

## Dynamic replay blocker

The pinned accepted research bundle now restores successfully at `/tmp/fsffl-accepted-review-bundle`, with the existing accepted commit and per-file SHA256 checks. It is no longer accurate to say that all accepted research inputs are unavailable locally.

A read-only P0/dynamic replay was attempted with the saved State/ROS revisions, existing accepted rules, no persistence writer and the normal current Sleeper acquisition. Its **first NFL-state GET failed through the execution proxy with HTTP 403**, before candidate inputs or dynamic fitting. Elapsed ~0.018 s, peak 169,092 KiB; this is a blocked acquisition and must not count as a dynamic memory benchmark. Do not substitute invented weekly stats, identities, P0 packets or timestamps.

## WR evidence gate

Saved ROS replay remains undercovered: Mingo/McMillan/McCaffrey have one source each; Noel/Hill/Aiyuk have none. Only McMillan and Noel appear in the preserved preseason raw ensemble. The existing approved fallback is scoring-gap-only and these subjects have no admitted strict-scorer partial. No numerical WR recovery is claimed. More admissible source evidence or a separately reviewed eligibility change is required.

## Remaining acceptance

After exact-head Stable/review and an authorized merge/deployment: confirm exact live SHA, restore readiness and memory, then observe one authenticated explicit refresh. Verify terminal Career coverage, coherent 3-Year/Career values in all views, Position & Depth state and persistence, peak memory/CPU, errors/restarts and physical user results. No plan/provider/schema/worker change or repeated failure loop is authorized by this receipt.

## Observed hosted refresh — 03:49:42 UTC

The user started exactly one authenticated refresh after deployment. Job `intelligence:33fc280d64114c0594e301220ca313a7`, State `703e822cd9186c3d1b7590d64a2479ff93763c451d1ac5c21d4c66c1f1dda846`. Core completed successfully in **118.847 s** at 03:51:41.569950 UTC. The new completion text correctly separates Career/Dynasty readiness.

- Forecast used the accepted immutable preseason fallback because only Razzball supplied eligible live full-season evidence. CBS served the wrong horizon, FFToday returned 403, NFL Fantasy lacked projection content. Source-health degradation remains explicit; no source minimum was lowered.
- Simulation kernel **6.495 s wall / 3.189 s CPU**; 50,000 trials, existing behavior.
- Career exact Y4-Y7 restore **3.005 s wall**, including a compatibility check. No reference long-horizon rebuild marker appeared.
- The new 334-player reference checkpoint was saved at 03:51:58.566724 UTC.
- Live P0 acquisition/scoring **13.388 s wall / 5.471 s CPU**, sampled RSS peak **483,422,208 B**, after-release RSS **423,395,328 B**.
- Accepted dynamic Foundation 4 materialization **198.434 s wall / 97.817 s CPU**, sampled RSS peak **486,268,928 B**. It completed at 03:55:34.172859 UTC.
- Expanded-cohort composition and final persistence produced **366 Career estimates** at 03:59:22.753301 UTC. It is a complete expansion, not only a reference checkpoint. Dependency fingerprint `b001f7cd7612ee81689c4144bdd7a66a0f6050fc155681c30aae4266a5ef5d11`.
- Final Career-backed presentation generation **ffae3672dcb9f9624816b1e7f03a24ed77c0ca5fa00f08e19075982d03aff419** was durably pointed to at 04:00:09.767284 UTC; atomic pointer phase completed at 04:00:11.511608 UTC. End-to-end through this save: **about 10 min 29 s** from the user action.
- No Render OOM, server-failed or restarted event during the observed run.

### Peak and capacity limits

Highest reported process high-water at final presentation: **513,142,784 B = 489.37 MiB**. The sampler's maximum earlier in fitting was 486,268,928 B. Render 30-second charged-memory samples reached **444,805,120 B = 424.20 MiB**; CPU reached the complete **0.5 allocation**. RSS and charged memory are different measures, and sampled container metrics can miss short peaks. The successful run does not establish comfortable headroom: process high-water is only ~22.6 MiB below the configured 512 MiB threshold and exceeds the 409.6 MiB application working target. Final observed RSS remains about 471.7 MiB. Preserve further memory/retention and concurrent-reader capacity work as an open gate; do not infer broad multi-user safety from one survivor.

Some compatibility reads still overlapped before the job (three start markers at 03:49:05–06), despite the exact-object in-flight coalescing working in the saved-input test. Do not claim every semantic-equivalent reader is coalesced. The guard intentionally distinguishes different immutable input objects/epochs; investigate producer-owned lightweight dependency receipts before broadening reuse.

### Publication and user-visible coverage

Read-only database verification confirms the final matching-State generation contains ready rostered-player 3-Year/Career lenses and ready Dynasty position rooms. All five screenshot subjects (Dak Prescott, Omarion Hampton, Quinshon Judkins, Drake London, CeeDee Lamb) now have finite 3-Year and Career indexes and ready row statuses in that saved publication.

Career covers **257 / 258 rostered QB/RB/WR/TE subjects**. The remaining explicit failure is **Dameon Pierce (`sleeper:player:8129`)**: no complete Y1 raw scoring row, CBS absent, Razzball only, verified current role unsigned; role evidence is not a return projection or proof of whole-season absence. His canonical roster row is preserved and no value is invented.

Current Position & Depth is **ready for every configured slot, including WR**, in this new publication. This is not a numerical fallback change: the formerly deficient team now has additional covered WR roster IDs `sleeper:player:3286` and `sleeper:player:4177`; its third WR slot is filled by the latter. Missing outlooks for the old undercovered subjects remain missing. The new exact State/roster permits the unchanged comparison to run. Do not claim the source-coverage policy issue was repaired by changing calculations.

Physical confirmation is pending. The assistant asked whether 3-Year/Career values and Current WR appear after one page reload, explicitly without another intelligence refresh. A saved ready publication is not itself proof of the user's rendered device state.
