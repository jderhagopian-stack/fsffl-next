## 2026-10-14 UTC — Career #405 bounded history completed; measured memory exception accepted

PR #454 code head `af38a4d9795a38a65c85639f262bab7873852503` preserves the accepted model calculations while storing unexpanded native feature columns and retaining only skinny horizon coordinates. Original predictor scope, row predicates, categorical/missing values, float64 matrices and fitting parameters are preserved; native fitting uses one worker and completed intermediates are released before the next phase.

The same saved Week 5 State `2fd788a858a6497425b2e066c77b3176e305030d6f7620cf25cf59ed3b30e061` completed Current → Foundation 4 → full Career/Shapley → matching-State Position & Depth: 353 Career estimates, 304 dynamic policy rows, 19 tails, all 252 roster rows, 243 available values and the same nine explicit unresolved outcomes. No provider acquisition or waiver processing was repeated. The player ledger records actual final values and failures.

Measured complete-path peaks: **418.29296875 MiB** and **416.5 MiB (436,731,904 B)**; final restored-bundle run elapsed **182.61s**. Both exceed the 409.6 MiB working target but remain below the **536,870,900 B (~512 MiB) actual hard cap**. The user explicitly accepts this measured reduced-target exception on 2026-10-14. Keep the working target and global 20% headroom policy unchanged; this is a specific Career acceptance disposition, not infrastructure authorization.

Original-vs-bounded materializer comparison with identical inputs/native worker count is exact: 304 rows / 19 tails, max delta **0.0**. The final restored-bundle run matches the preceding bounded Career run exactly across all 353 estimates and every component. Relative to the earlier multi-thread run, Current/tails are unchanged and maximum Y4–Y7/Career variation is 0.0000198619; this numerical distinction is retained rather than claiming universal zero drift. Frozen-335 parity is a separate CI gate (the memory-code GitHub run 38572789744 passed 172 checks with Shapley/Career deltas both 0).

The existing background materializer has an opt-in, process-shared immutable model-version bundle restore, streaming and hash-checking the accepted release archives and pinned `be2541a4` programs. All eight downloads actually succeeded and verified in this run; no replacement research, new source, model fitting method, second lifecycle owner or page-read acquisition was introduced. Explicit mounts keep priority. Required pandas dependency is included. Local hosted-bridge/history/restore selection passes 15 tests. Final code GitHub CI is running; keep draft until the remaining global gates pass, then follow Management #6134676365 / #6154167179 conditional release authorization.

**Observed final-code GitHub Actions:** exact executable head `af38a4d9795a38a65c85639f262bab7873852503`, [CI run 38573942462](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/38573942462), **SUCCESS: 177 checks**, frozen Shapley/Career max deltas both **0**. Global saved-input gates now pass under the explicitly accepted measured memory exception. Next: stable exact-head full suite, conditional merge and existing-service deployment; no further approval required.

## 2026-10-14 UTC — Career #405 saved Week 5 rerun and real CI

PR #454 remains draft. Code `09e7ea36…` completes 353 Career estimates and all 252 matching-State roster rows (243 values, nine unresolved). No repeat acquisition. Training projection preserves exact values and reduces full-path RSS to 527.469 MiB, still above 409.6 MiB. The main continuity conflict is resolved and real GitHub focused CI run 38508053037 now executes. Local focused groups pass 168 tests. See [the current executed checkpoint](workstreams/CAREER_COVERAGE_PR2_20261011.md) and player ledger.

# Superseded operations document

The former contents are preserved at [`archive/ACTIVE_WORKSTREAMS_20261006.md`](./archive/ACTIVE_WORKSTREAMS_20261006.md).
Current cross-workstream status is [`CURRENT_OPERATIONS.md`](CURRENT_OPERATIONS.md); detailed architecture evidence remains in [`workstreams/ARCHITECTURE_RECOVERY.md`](workstreams/ARCHITECTURE_RECOVERY.md).

Do not use this historical snapshot as current status.
