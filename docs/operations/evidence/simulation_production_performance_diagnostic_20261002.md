# Simulation production performance diagnostic — 2026-10-02

## Scope

This is the deferred narrow full-call production profile for the accepted Simulation 2.0 runtime. It does not reopen Simulation semantics, trial-count research, RNG equivalence, or accepted #324-#333 behavior.

Production authority remained unchanged throughout:
- 50,000 canonical trials;
- `numpy-pcg64-batched-gauss-v1`;
- batch size 500;
- Python 3.12.10.

Profiler instrumentation landed in #344/#345 and is dormant unless the explicit diagnostic switch is enabled. It does not change output, replay identity, model authority, or RNG consumption.

## Representative governed FSFFL run

A clean isolated hosted run on the current production path reproduced the physical ~126-second Simulation interval.

Measured Simulation composition:
- Forecast attachment: **0.204s**
- lineup/static compilation: **1.905s**
- bye-aware weekly scoring/input panel: **11.401s**
- input/schedule materialization: **0.001s**
- 50k kernel + result aggregation: **105.595s**
- Team Utility / Analytics view assembly: **8.695s**

Measured total of those phases: **~127.8s**.

Kernel profile:
- RNG generation: **1.481s**
- vectorized matchup/scoring: **1.175s**
- cooperative foreground yield: **~0.192s**
- per-trial setup: **~0.661s**
- per-trial matchup/H2H reconstruction: **~11.267s**
- standings: **~9.064s**
- playoffs/championship: **~15.824s**
- team-of-origin future-pick ordering: **~27.558s**
- Multiverse representative-world work: **~0.519s**
- common-world setup: **~0.001s**
- residual kernel tail: **~9.589s**
- result materialization: **0.192s**

The sampled kernel subphase values are hotspot estimates and should not be summed as a second exact kernel total. The exact outer kernel wall time is 105.595s.

## CPU and memory

The run was CPU-limited, not memory-limited.

- Render Free CPU repeatedly reached the **0.15 CPU** service limit during the run.
- Kernel wall time was 105.595s while measured process CPU time was 15.834s.
- Simulation peak RSS remained **388,489,216 bytes**, below the engineering budget of **429,496,720 bytes** and the Render hard limit of **536,870,900 bytes**.
- No new process memory peak was created by the kernel itself.
- Cooperative foreground yielding contributed only ~0.192s in this run, so browser foreground pressure does not explain the current ~126-128s Simulation duration.

The current hosted logger did not emit the coordinator's exact heavy-lane wait/reclaim INFO records. No competing heavy phase was observed at Simulation entry/exit and the completion snapshot showed `active=simulation waiting=0`; heavy-lane admission was therefore not a material contributor in this isolated run.

## Persistence/publication

Persistence is not part of the expensive Simulation kernel.

After Simulation/Value/Intrinsic, terminal publication persistence measured:
- State/team snapshots: **1.910s**
- derived artifact encode/write: **1.844s**
- atomic manifest/pointer: effectively **0s**

Total terminal publication persistence was ~**3.75s**.

Long ~26-30s persistence writes observed earlier in the acceptance journey were startup/restoration staging and occurred outside the measured Simulation call. They must not be attributed to Simulation runtime.

## Interpretation against prior baselines

- Legacy Python physical Simulation: ~**173s**
- Earlier hosted NumPy interval: ~**59s**
- Current production path: ~**126-128s**

The current runtime is still roughly **26-27% faster than the ~173s legacy physical path**, despite doing substantially more per-world work.

The earlier ~59s hosted NumPy result is not an apples-to-apples current baseline. The current profile shows that the regression is **not RNG**: RNG is only ~1.5s of a 105.6s kernel. The largest costs are later Simulation 2.0 capabilities and their supporting per-world Python work, especially team-origin future-pick ordering, playoff/championship processing, and H2H reconstruction.

Multiverse itself is cheap (~0.5s), and common-world setup is negligible.

## Bottleneck ranking and next optimization target

Highest-value measured targets:
1. **team-of-origin future-pick ordering (~27.6s)**
2. **playoff/championship processing (~15.8s)**
3. **per-trial matchup/H2H reconstruction (~11.3s)**

A fourth meaningful non-kernel target is Team Utility / Analytics assembly at ~8.7s.

The safest first performance work should preserve all current authority and exact output semantics:
- remove or batch-vectorize unconditional full-schedule H2H reconstruction, computing H2H only where governed record ties actually require it, or deriving equivalent H2H matrices in batch;
- then reduce repeated Python list/dict/sort work in exact team-origin slot ordering;
- only then consider batching playoff bracket work.

The first two are coupled and may recover a meaningful portion of the current runtime, but no savings target is promoted until output-exact equivalence and a hosted 50k benchmark prove it. Do not lower trial count, alter RNG, weaken tiebreak semantics, or remove accepted Simulation 2.0 outputs to gain speed.

## Management disposition

The diagnostic is complete. No broad model correction is warranted.

- Keep canonical production authority at **50,000**.
- Keep NumPy/PCG64 batch 500.
- Do not spend further effort optimizing RNG.
- Treat CPU-bound team-origin/playoff/H2H Python work as the next bounded Simulation performance opportunity.
- Any implementation must prove exact result/replay equivalence before promotion.
