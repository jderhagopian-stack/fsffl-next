# Career Coverage #405 — PR2 checkpoint

Date: 2026-10-11

- Repository: `jderhagopian-stack/fsffl-next`
- PR: #454, draft
- Branch: `career/dynamic-materializer-20261011`
- Starting head: `dbef69412e488e747b3caaf57a02fdf46c5adff4`
- Tested code head: `8fbf4781d0733e978d13dc7426b18b799b3b22c6`
- Durable derived-output destination: private Library folder `/FSFFL NEXT/_implementation_temp` (available; no provider payloads will be stored in GitHub).

## Current durable evidence

The October 11 governed P0 run processed 507 dynamic subjects but saved only an aggregate PR comment. Its per-player outputs and failure rows are unavailable and will not be inferred or reused. Do not rerun that 507-player cohort. The next authorized refresh, after the governed adapter is made runnable and exact-State inputs are validated, is roster-only for 27 dynamic players. Persist each success, each player failure, provenance, State identity, and evaluation timestamp to the private destination before Career composition.

The accepted source/rights policy, frozen 335-player reference, Shapley contract, and model authority remain unchanged. No refit, production-model change, merge, deployment, or new infrastructure is authorized.

## Acceptance sequence

1. Run the governed P0 refresh for only the 27 dynamic roster candidates; persist and verify the private artifact before further analysis.
2. Compose supported roster Career values with the existing Shapley/Career contract and prove frozen-reference parity.
3. Investigate and explicitly account for every unsupported roster player; do not omit, zero-fill, or invent values.
4. Propose a bounded Explore waiver cohort from supported candidates; do not materialize all 480 outside-reference waivers.
5. Wire matching-State publication and test actual identity/provider resolution for a newly rostered outside-cohort player.
6. Reduce the complete Career materializer peak below the existing ~410 MiB budget.

## This checkpoint

This session confirmed the repository write path and private durable destination. No provider acquisition has run. GitHub branch-targeted writes are confirmed. At head `9ad57eb994b48b812a53b4a3c4ee10fd864cf5c7`, focused CI and PR164 focused corrective regression passed; stable full suite skipped because the PR remains draft. The current tool session has no local checkout, and Actions capabilities expose run/artifact reads plus failed-job reruns, but no workflow dispatch or command execution. Therefore the roster-only P0 adapter cannot be launched from this chat yet. Next: establish an authorized execution path for the existing adapter that is constrained to these 27 roster IDs and can persist sanitized derived outputs into the private Library destination before Career composition. Do not repeat the 507-player refresh.

## Implementation checkpoint — 2026-10-11

Branch-targeted commits add `build_career_forward_from_canonical_p0`: it validates canonical Y1/Y2/Y3 cohort coverage, calculates Shapley over the supplied cohort, then calls the existing Career contract. It does not calculate candidate-alone marginals and fails closed on missing horizons or mismatched cohorts. Fixture tests prove parity with direct existing Shapley/Career composition. A bounded Explore selector (default 50, maximum 100) ranks supported waiver candidates; tests cover limits and stable ranking. A stale-State Position & Depth publication regression asserts fail-closed behavior. CI explicitly installs pandas for dynamic-candidate tests.

The 335-player long-horizon materializer now releases raw feature joins after constructing narrow current/terminal snapshots and before loading the historical route panel; it also drops route panels and prediction caches before allocating publication tables. This is a code-level lifetime reduction only. The full materializer has not been run in this environment, so the measured 490,928 KiB baseline is not yet shown below 410 MiB, and no RSS benchmark result is claimed.

At tested code head `8fbf4781d0733e978d13dc7426b18b799b3b22c6`, PR CI, PR164 focused corrective regression, and Live Forecast corrective trace passed; stable full suite skipped while the PR remains draft. No Career candidate has been newly scored or reported as covered. Dynamic Career composition still requires the unavailable canonical P0 packets and matching cohort Shapley outputs; the existing Career composer remains strict about ready Current Shapley, matching Y4–Y7/tail cohorts, and frozen reference authority. No provider acquisition or production-model change occurred.

**Next:** inspect final CI, add/fix a focused benchmark if repository fixtures support exercising the materializer path, and obtain an authorized runner for only the exact-State 27-player P0 refresh. Persist its player-level results privately before dynamic composition. Keep #454 draft.
