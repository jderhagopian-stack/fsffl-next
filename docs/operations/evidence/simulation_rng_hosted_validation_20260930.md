# PR #311 hosted Simulation RNG validation — 2026-09-30

## Decision status

**Hosted resource gate failed. Production adoption is not supported by this run.** The experiment completed and atomically published all governed capabilities, but its measured process peak exceeded the unchanged free-Render hard memory limit. The service was restored to `main` / #310. This result is not a Simulation correctness failure, but it is a deployment-safety failure.

## Exact execution identity

- Service: `fsffl-next-private-beta` (`srv-dae6k7vqj5pc73af7bt0`), free plan, Virginia.
- Experimental PR: #311, branch `work/simulation-modernization`, exact deployed commit `689f6c979aca7b0f06cae003a8c1f6ede3aed7a8` (draft, not merged).
- Code under test: `4b87e80ac1ce0881938a3dbe21b229898032e824`, plus operations-only commits through the deployed head.
- RNG: `numpy-pcg64-batched-gauss-v1`, batch 500, 50,000 trials. Legacy Python Random replay remains supported.
- Experimental Render deploy: `dep-daun7aqd0e5s73arvjm0` (live 20:42:04Z, deactivated on rollback).
- Restored live deploy: `dep-daunc2nlk1mc73di9b1g`, exact `main` commit `3671ba0e6ff29ab750b71b8aaa467be0f56e55a9` (live 20:52:09Z). Service branch is `main`; auto-deploy is `On Commit`.
- Temporary acceptance flags were reset to their prior disabled state; temporary RNG protocol/batch settings were removed.

## What passed

The controlled state-first acceptance exercised clean State acquisition, team selection, first-load Market/value-lens materialization, cold Home/Franchise/League/Market surfaces during the refresh, player-history reads, and the real intelligence build/publication. These reads occurred while refresh work was in progress; the recorded surface checks were issued serially, so they do not prove simultaneous parallel-request latency for every requested consumer.

At 20:47:48Z, acceptance recorded completed job `intelligence:28260d3daea647928bf95f2e09bb0f28` for State `96befa963b8874d7b548c879adc4ebafbafd19c0bd599f5bf1e71ef10de8b871`, published generation `c0a601f9f1b6f2629b2d2e1bb471bb1ef6223806d0c140a9792b1d29f97aeee8`. Readiness was full for Forecast, Simulation, Current Value and Intrinsic; Forecast covered all 666 authoritative scored subjects, Current Value was full, and Intrinsic had 335 estimates for 2026–2028. The acceptance harness confirmed `working_generation_active=false` and terminal job status `completed`.

The first-load Market workspace and `all` / `rostered` value-lens work ran during the refresh. Both lens universes later reported Intrinsic ready. After rollback, main served the restored canonical State `0599e90541d1f43a64a23ed33e89f30209d3acd9503979f7f0121665adfbbd07` with Simulation true and runtime readiness full; both Market universes reported Intrinsic ready. Their Forecast coverage was truthfully degraded (rostered 223/244; all 335/871), which is separate from this RNG/resource gate.

## Resource, timing and responsiveness findings

The unchanged app-side limits were a soft budget of `429,496,720` bytes and a hard limit of `536,870,900` bytes.

- Startup RSS was about 293.7 MB; startup high-water mark was 297.9 MB.
- Refresh began 20:43:10Z at RSS 335.0 MB. Publication completed 20:47:26.692Z: about **256.7 seconds end to end**.
- Forecast completion was logged at 20:44:41.993Z, Simulation completion at 20:45:40.987Z, Value at 20:46:00.898Z, and Intrinsic reconciliation at 20:46:23.886Z. The interval from the Forecast-complete marker to Simulation-complete was about **59.0 seconds**; this build did not emit a separate Simulation-start timestamp, so 59 seconds is a phase-boundary estimate rather than a precise isolated kernel duration.
- By Forecast completion the process high-water RSS had reached `576,552,960` bytes (576.6 MB), which exceeds the hard limit by `39,682,060` bytes (39.7 MB). At final acceptance, current RSS had fallen to `403,820,544` bytes, but its high-water mark remained over the limit and the harness failed `within_memory_budget`.
- Render's 30-second `memory_usage` samples peaked at `530,784,260` bytes at 20:44Z, about 6.1 MB below the platform's reported `536,870,900`-byte limit. The process-level phase telemetry therefore caught a higher brief peak than the coarse Render sample. The app acceptance correctly treated the high-water mark as the governing result.
- Render CPU samples sat at the service limit of `0.15` cores through nearly all of 20:43–20:48Z. The shorter NumPy kernel did not make the full refresh responsive on this free instance.
- App-side resource counters showed 7 acquisitions and 7 completions, with no queued waiters at final acceptance. The foreground surface checks overlapped the overall build, but were sequential within the harness: Home 1.598s, Franchise 1.000s, League 9.996s, Market 1.192s, all-player lenses 1.492s, rostered lenses 1.895s (17.173s total). Product Context was included in a separate clean-State probe at 7.495s with League at 4.095s (11.590s total). These are real hosted latencies, not a fully parallel Home/My Team/Product Context load test.
- No unexpected restart/OOM was observed during the experimental refresh. The later shutdown at 20:52 was the intentional replacement of the experimental instance during rollback.

The high-water sample does not isolate the allocation responsible. A player-history sample observed 572.17→572.20 MB resident with no new high-water increment; subsequent Forecast instrumentation reported RSS falling from 463.53 to 394.82 MB. Therefore the evidence does not justify attributing the peak specifically to Gaussian generation, player history, or any one capability. It does establish that batch-500's faster isolated kernel did not make the real refresh fit the process's enforced memory envelope.

## Statistical and downstream evidence retained

The original 100 independent seed labels × 50,000 study remains unchanged: probability ±0.002 and rank-distribution TV ±0.005 passed; expected-wins ±0.001 remains **inconclusive** (worst point difference +0.002395). The deterministic changed-State fixtures continue to match across RNG protocols for the tested Team Utility and bilateral Decision directions/sign, lineup and position-strength/resilience Analytics, and scoped Search candidate identity/order, including a symmetric near-boundary case. These fixtures are bounded evidence, not proof of general downstream equivalence.

Local full suite was 1,899 passed with one Starlette deprecation warning. Exact code/CI/review details remain in `simulation_rng_changed_state_validation_20260930.md`. No PR merge or production adoption occurred.

## Remaining gate / next executable action

Return this complete evidence to Management. Keep PR #311 open/draft and private beta on `main` / #310. Production adoption remains withheld because the hosted hard-memory gate failed. The next work should identify the short-lived allocation peak within the refresh lifecycle and establish a safe margin below the same hard limit before any repeat of this hosted experiment; preserve 50,000 trials, modeled distributions, RNG/replay versioning and both replay engines. Then rerun the controlled batch-500 hosted journey, including true concurrent foreground reads, completion/readiness, and restart restore. Do not merge or adopt without a separate Management decision.
