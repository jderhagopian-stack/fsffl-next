# Simulation RNG changed-State downstream validation — 2026-09-30

## Scope and outcome

This bounded deterministic regression was added to PR #311 to cover the previously missing downstream product path without changing the approved 50,000-trial contract. It compares the legacy Python Random stream with `numpy-pcg64-batched-gauss-v1` at batch 500 on identical State, Forecast, seed, and changed-roster inputs.

The tested clear trade moves a much stronger player between teams. Team Utility and real bilateral Decision direction/sign agree across protocols. A symmetric near-boundary trade produces neutral Decision directions under both. The optimized lineup and published position-strength/resilience inputs agree exactly. The real scoped Search builder returns one candidate for each of the before/after States; candidate identity and order agree across protocols for each exact State.

This is a regression fixture, not a broad power study or full production-league decision study. Cardinal Value inputs are held constant because Value is upstream of Simulation and is not recomputed from RNG outcomes. No change to Value semantics or output is claimed. The originally approved statistical result remains **inconclusive at ±0.001 expected wins**.

## Reproduction

```sh
uv run --extra web --with pytest pytest \
  tests/test_live_simulation_runtime.py \
  tests/test_product_scenario_cache.py -q
```

The changed-State decision regression runs legacy and NumPy/PCG64 Simulation at 50,000 trials for both baseline and swapped-roster State, first with a clear forecast gap and then with equal means at the decision boundary. The Search regression separately changes the same two-player roster State into a WR fixture and calls `build_scoped_trade_candidates` with authoritative typed Cardinal Value scores. Both before and after States produce one candidate; its owner/send/receive identity and ordering are the same under both RNG protocols.

The clear case yields team A expected-wins/playoff/first-place directions `worsens` and team B `improves` under both protocols. Both cases classify the whole bilateral shape as `mixed_or_incomplete` because asset-portfolio and championship inputs are intentionally absent from the small fixture. In the symmetric boundary case, both teams' available competitive and resilience directions are `unchanged` under both protocols. This is evidence for these deterministic cases only; it does not prove general equivalence of all downstream recommendations.

## Validation status

- Focused runtime/cache tests: 19 passed before the final Search/cache-key additions; latest focused runtime + scenario-cache run: 12 passed.
- Full local suite after those additions: 1,897 passed, one Starlette deprecation warning.
- Exact PR head `b26fe97c67dded54da1bee92a756f451e99ac09d`: GitHub CI run #4060 and configured focused runs #953, #736, #698, and #999 succeeded.
- A fresh `@codex review` was requested on that exact head (PR comment 5917929258); no response for that exact head was present at handoff time. The available older review finding referenced `d2e0f270b8`; its claimed truncated operations files are not present in the reconciled head (the full current-main histories are retained).
- That fresh review subsequently found a P1 durable-key mismatch: experimental Simulation writes included RNG-manifest fields while scenario-cache reads used a different key. The correction makes durable scenario writes use the exact same `_durable_key` used by reads, and binds that key to process-start protocol, batch, count, seed, Python/NumPy runtime, and model version. A restart-style regression clears the process cache and proves a NumPy artifact is reused from the durable store without a second Simulation call. Configuration is now snapshotted at process start so runtime env changes cannot make the selected protocol disagree with persistence model-version constants.
- Focused runtime/cache suite after that correction: 22 passed. Full local suite: 1,898 passed, one Starlette deprecation warning. Startup-configured batch-500 probe resolved model version `next8-live-simulation-analytics-v8:numpy-pcg64-batched-gauss-v1` and cache identity `numpy-pcg64-batched-gauss-v1;batch=500;count=50000;seed=20260905;runtime=python-3.12.14;numpy-2.5.3`.
- Controlled hosted validation did not run. The Render dashboard browser secure authentication request returned `declined`; the browser also explicitly rejected navigation to the Google identity provider after its permission was declined. No credentials were read by the agent, no branch/env/service changes were made, and the service remains on main / deployed #310.

## Next executable action

After the durable-key corrective clears a fresh exact-head review and CI, and the user explicitly reauthorizes a fresh secure Render email/password sign-in request, configure the private-beta service temporarily to the exact experimental branch/head with
`FSFFL_SIMULATION_RNG_PROTOCOL=numpy-pcg64-batched-gauss-v1` and `FSFFL_SIMULATION_RNG_BATCH_SIZE=500`, capture the full refresh/Simulation/heavy-work/RSS/concurrent-read/publication/restart evidence, then restore the main/#310 service configuration. Do not merge or adopt the experimental protocol. Return that complete evidence to Management for the separate adoption decision.
