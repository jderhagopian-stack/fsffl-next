# FSFFL NEXT — Hosted Evidence and Performance Decision

Date: 2026-09-20

## Deployment alignment

Current validated main `a3c8a65e45b484b342ad3b4351cc8d8d81811971` was deployed through the existing Render service.

- service: `fsffl-next-private-beta` (`srv-dae6k7vqj5pc73af7bt0`)
- deploy: `dep-dao09foae00c73aadkjg`
- commit: `a3c8a65e45b484b342ad3b4351cc8d8d81811971`
- status: `live`
- finished: 2026-09-20T16:08:54Z
- build: successful
- startup: application startup complete; Uvicorn serving on port 10000
- root GET without beta credentials: 401 as expected

The standard-chat environment cannot read private beta credentials or originate an authenticated browser session, so authenticated current-SHA smoke requests cannot be manufactured here. This is an execution boundary, not evidence of a failed deploy.

## Hosted evidence recovered

The service already emits request-wall-clock logs for major product endpoints, Market cache timing, and post-trade Simulation phase timing.

### Useful-path observations from prior hosted beta use

9/13 session:
- product context first authenticated response: 2.796s; later 0.012s
- My Team: 0.253s; later 0.005s
- Market quick workspace: 1.261s; later 0.201s
- Market full workspace: 14.212s cold; later 0.313s
- Trade browser: 0.034s
- Trade quick: 0.302s
- Trade analyze: 12.816s
- Trade simulate: 1.898s with exact Simulation cache reuse

9/19 session:
- product context first responses on restarted instances: 3.204s / 2.577s, then 0.013s / 0.097s
- My Team usually 0.005–0.261s, with one 13.496s outlier
- Market quick workspace: 2.234s
- Market full workspace: 19.165s
- Trade browser: one 3.486s observation

### Cache and coalescing evidence

Market structural Search:
- cold catalog: 0.792s for 654 candidates on 9/13
- cold catalog: 1.100–1.599s for 666 candidates on 9/19
- exact catalog hits: usually effectively 0s to ~0.3s

Market workspace:
- quick/cold governed workspace observed at about 1.0–1.9s
- full cold workspace observed at about 14.0–18.9s
- later true hot hits collapse to subsecond
- concurrent requests can wait behind an in-progress first build, explaining some "cache_hit=true" wall times of several seconds rather than duplicate recomputation

Post-trade Simulation:
- one hosted phase record: preparation 0.574s, simulation-or-reuse 0.800s, postprocessing 0.201s, total 1.574s, `cache_hit=True`
- existing durable pre-current-SHA hosted evidence measured a fresh unchanged 50,000-run changed-roster Simulation at about 85.0s and exact reuse at about 1.2s
- full deep frontier historically measured roughly 316–332s because it chains bounded full analyses

### Connect / restore evidence

Observed hosted requests show repeated successful background connect / refresh/status behavior across sessions:
- background connect/status returned 200 on 9/13
- background refresh/status returned 200 on 9/19
- another 9/19 session successfully re-entered background connect/status after authentication

This is useful evidence that the background path is functioning, but it does not by itself prove every Phase 1/2 exit criterion. No explicit user-perceived latency records were present in the queried Render logs, and no direct hosted log line proved the exact restore-before-refresh ordering.

## Measured bottleneck classification

### Common navigation / first-use path

The progressive Market architecture is working as intended: first useful Market evidence is low-single-digit in observed sessions while the full enriched workspace remains much slower. Exact Search/workspace reuse is effective.

### Deep analysis

Fresh full-fidelity 50,000-run Simulation remains the strongest known deep-analysis bottleneck. Exact reuse is already highly effective.

However, after deploying current SHA today, there is not yet a fresh current-SHA `cache_hit=False` Simulation phase record. The only phase-level record recovered is a cache hit. Therefore a kernel or orchestration optimization is **not yet justified by current-SHA hosted phase evidence**.

## Performance decision

Do not implement a speculative Simulation rewrite.

Next bounded diagnostic:
1. obtain one authenticated current-SHA trade on an exact changed state with no reusable Simulation artifact;
2. capture endpoint wall clock plus phase timing: preparation, Simulation execution/reuse, postprocessing and scenario-cache subphases where available;
3. repeat the exact request once to verify reuse;
4. choose the narrowest optimization only from the dominant fresh phase;
5. preserve 50,000 runs and identical Simulation semantics.

Potential techniques such as deterministic preprocessing reuse, unchanged-team distribution reuse, or safe vectorization remain hypotheses until that measurement exists.
