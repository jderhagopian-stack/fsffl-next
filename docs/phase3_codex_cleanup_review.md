# Phase 3 Codex reliability cleanup

This short cleanup pass was performed before further Phase 3 feature expansion.

## Production findings

- PR #84 evaluated spotlight: valid. The interactive Opportunity workspace now performs one bounded server-owned bilateral evaluation by default so `most_promising_evaluated` can exist without Home launching Search/Decision work.
- PR #84 stale/wrong-team workspace: valid at the shared Opportunity owner even though the original Home-local fetch path was removed before merge. Opportunity responses are now keyed to captured league/team/state context and stale responses are discarded; context changes clear stale shared payloads.
- PR #84 retryable readiness: preserved through the existing Opportunity retry loop; retryable non-ready payloads are not treated as durable ready workspace.
- PR #77 Behavioral RLS bootstrap: valid. Runtime bootstrap now idempotently enables RLS on the same private Behavioral tables created by the initializer.
- PR #82 NaN latency persistence: valid. Non-finite elapsed time is rejected before logging or persistence.
- PR #76 historical identity timezone: valid. Identity keys canonicalize equivalent instants to UTC before hashing.
- PR #76 initial checkpoint race: valid. The upsert itself now refuses to move `last_completed_at` backward.
- PR #71 lineup fingerprint: valid adjacent correctness issue. Forecast reuse now fingerprints lineup requirements used by scoring coverage.
- PR #71 future evidence reuse: valid adjacent correctness issue. Forecast evidence that postdates a replacement State is not reused.

## Test-hardening findings

These were test-strengthening issues rather than confirmed production defects, and were repaired because they were cheap and directly cover the affected contracts.

- PR #81 now executes the sync-state renderer against a deterministic DOM stub and verifies checking/current/stale visible content plus `role=status` and `aria-live=polite`.
- PR #79 waits for the full selective checkpoint to become restorable before constructing the restarted runtime.
- PR #75 synchronizes deterministically with the failing persistence write instead of sleeping for an arbitrary duration.
- PR #74 persists and restores a representative non-empty nested Value estimate.
- PR #72 asserts the lightweight Sleeper sync probe is invoked while the full loader remains unused for unchanged state.

## Authority boundaries

No presentation surface performs Search, Decision, Simulation, Value, or Behavioral model logic. Home remains presentation-only and does not make Opportunity API requests. Search still generates candidate structures; Decision remains the owner of bilateral consequences; presentation consumes server-owned output. No model coefficient or authority hierarchy is changed by this cleanup.
