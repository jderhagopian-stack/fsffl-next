# NEXT-4 Exit Review

This is the governing closeout checklist for NEXT-4 Team Utility & Simulation.

## Promotion states

- **AUTHORITATIVE** — validated enough for default NEXT behavior.
- **PROVISIONAL_GOVERNED** — real effect with incomplete evidence; explicit, versioned, uncertainty-aware, and future-updatable.
- **CHALLENGER** — implemented/testable but non-authoritative.
- **OUT_OF_SCOPE** — belongs downstream under the charter.
- **NOT_READY** — missing acceptable implementation or violates authority/provenance requirements.

NEXT-5 may consume AUTHORITATIVE and PROVISIONAL_GOVERNED NEXT-4 outputs. It must not silently depend on CHALLENGER or NOT_READY behavior.

## Current classification

| Component | Status | Basis | NEXT-5 blocker? |
| --- | --- | --- | --- |
| Exact legal lineup optimization | AUTHORITATIVE | Dynamic-programming optimizer under canonical league rules; FLEX/Superflex joint optimization tested | No |
| Real-roster replacement impact | AUTHORITATIVE | Re-optimizes remaining roster rather than using arbitrary average starter | No |
| Missing forecast / unavailable roster handling | AUTHORITATIVE | Missing evidence surfaced; taxi/IR unavailable unless canonical state changes | No |
| Team scoring mean | AUTHORITATIVE | Sum of optimized NEXT-2 fantasy-point forecast means | No |
| Team scoring covariance | PROVISIONAL_GOVERNED | Independence assumption is explicit; covariance challenger/backlog recorded | No |
| Team scoring distribution family | PROVISIONAL_GOVERNED | Transparent non-negative normal approximation pending richer empirical fit | No |
| Competitive simulation | AUTHORITATIVE | Reproducible seeded Monte Carlo; wins/playoff/first-place authority only | No |
| Default simulation scale | PROVISIONAL_GOVERNED | 50,000 supported/default; future profiling may vary sample size by task | No |
| Calculated competitive-state contract | AUTHORITATIVE | Separate from owner posture; explicit policy input; future leakage rejected | No |
| Competitive-state thresholds | PROVISIONAL_GOVERNED | Explicit versioned policy until historical calibration is sufficient | No |
| Owner strategic posture separation | AUTHORITATIVE | Wrapped beside calculated state; cannot rewrite simulation or classification | No |
| Roster resilience | AUTHORITATIVE_FOUNDATION | Derived from actual replacement pathways; current metrics intentionally limited | No |
| Non-collapsing TeamUtilityVector | AUTHORITATIVE | Competitive outcomes, asset economics and resilience remain typed/separate | No |
| Scalar franchise-utility mapping | PROVISIONAL_GOVERNED / ABSENT | No arbitrary blended score; future mapping requires evidence | No, provided downstream consumes structured vector/deltas |
| Team state assembly | AUTHORITATIVE | Orchestrates State + Forecast + Value + Simulation without rewriting upstream authority | No |
| Before/after scenario deltas | AUTHORITATIVE | Structured competitive/resilience/economic deltas; no recommendation logic | No |
| Generic runtime sanity harness | AUTHORITATIVE_ORCHESTRATION | League-wide runner consumes canonical state + explicit Forecast/Schedule/Policy inputs; no league-specific logic or hidden defaults | No |
| Runtime Sleeper acquisition support | AUTHORITATIVE_DATA_BOUNDARY | Live provider payload acquisition remains upstream of canonical normalization and refuses historical masquerading | No |
| Controlled sanity invariants | AUTHORITATIVE_VALIDATION | Superflex depth, lineup monotonicity, simulation reproducibility, scoring monotonicity, posture separation | No |
| Real-league adversarial sanity pass | DEFERRED_VALIDATION | Use a real canonical league state when a networked runtime is available; diagnostic and regression-generating, not universal calibration truth | No |
| Authority / anti-double-counting audit | COMPLETE | Explicit audit + automated downstream import guard | No |
| Bilateral trade evaluation | OUT_OF_SCOPE | NEXT-5 Trade Decision | No |
| Search / package balancing | OUT_OF_SCOPE | Search/Optimization | No |
| Reports / analytics / charts | OUT_OF_SCOPE | NEXT-7 Analytics/API + Presentation | No |

## Controlled sanity evidence

Automated CI sanity cases currently verify:

- elite Superflex QB marginal impact is larger when QB depth is weak than when strong;
- adding stronger depth cannot reduce optimized lineup points;
- identical simulation inputs plus seed reproduce identical outputs;
- raising a team's scoring mean improves expected wins and playoff/first-place probability under controlled identical conditions;
- owner strategic posture cannot alter calculated team state;
- scenario comparisons preserve channel separation and reject incompatible economic scales;
- team assembly fails closed when a calculated-state classification is requested without an explicit governed policy;
- the generic league sanity runner evaluates every team through the same authoritative path;
- the runtime runner is reproducible for identical inputs and rejects future policy evidence.

## Runtime validation path

The generic runtime path is complete:

**runtime league id -> SleeperLiveSource -> canonical NEXT-1 LeagueState -> explicit NEXT-2 forecasts + schedule + policy -> NEXT-4 lineup/scoring/simulation/utility -> structured diagnostic result**

The league identifier and fetched provider payload are runtime data and are not committed to git. See `next-4-runtime-sanity.md`.

## Deferred real-league validation

The real-league adversarial pass remains a required tracked validation task, but it is no longer an architectural completion gate for NEXT-4. When a networked execution environment is available:

1. Execute the real-league adversarial sanity evaluation using the runtime harness, canonical league state, and current admissible forecast inputs.
2. Review a small set of pre-registered realistic cases with knowledgeable human judgment before revealing outputs where useful.
3. Repair only generalizable defects; do not encode one league's preferences as universal coefficients.
4. Add any discovered generalizable failures to the permanent regression suite.

The PR changed-file scope and authority boundaries have been reviewed and are clean; reporting remains in NEXT-7 and trade/search logic remains downstream.

## Non-blocking future improvements

See `next-4-future-improvements.md`. Key items include calibrated player covariance, richer weekly scoring distributions, injury pathways, simulation caching/delta computation, empirical competitive-state thresholds, deeper resilience metrics, historical point-in-time backtesting, and the deferred real-league adversarial pass.

## Exit conclusion

NEXT-4 architecture, orchestration, authority boundaries, and controlled behavior are complete enough to merge and serve as the authoritative upstream foundation for NEXT-5. Governed provisional assumptions remain explicit and future-updatable. The real-league adversarial pass is preserved as deferred validation and must generate regression coverage for any generalizable defect it reveals.