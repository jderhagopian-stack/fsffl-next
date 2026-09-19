# Legacy FSFFL Concept Inventory

Legacy FSFFL is a source of lessons and test cases, not the NEXT specification.

Each material concept will be classified as `RETAIN`, `RE-DERIVE`, `REDESIGN`, `RETIRE`, or `INVESTIGATE` before implementation authority is granted in NEXT.

| Concept | Initial disposition | NEXT direction |
|---|---|---|
| Point-in-time league reconstruction | RETAIN / REDESIGN | Make foundational to all historical calibration and reproducibility. |
| Bilateral trade utility | RETAIN / RE-DERIVE | Preserve the concept; rebuild on canonical team state and franchise utility. |
| Competitive state vs owner strategic posture | RETAIN | Keep calculated competitive state separate from explicit owner preference. |
| Monte Carlo competitive simulation | RETAIN / REDESIGN | Preserve simulation authority; improve caching, deltas, uncertainty contracts, and reproducibility. |
| Market value | RETAIN / REDESIGN | Treat as market evidence/price, not universal intrinsic truth. |
| Team-specific value | RETAIN / RE-DERIVE | Derive explicitly from marginal franchise utility. |
| Pick valuation | RE-DERIVE | Point-in-time distributions, uncertainty, class strength, order information, and historical evidence. |
| Projection system | REDESIGN | First-class ensemble/forecast engine with source-specific validation and uncertainty. |
| Age/development curves | RE-DERIVE | Empirical position/horizon-aware curves where supported. |
| Positional scarcity / replacement | RE-DERIVE | Compute from league state and roster rules rather than generic constants when possible. |
| Consolidation/package effects | INVESTIGATE / RE-DERIVE | Model only residual effects not already captured by roster utility, scarcity, liquidity, or replacement. |
| Liquidity / transaction friction | RETAIN / RE-DERIVE | Separate market transaction dynamics from intrinsic value. |
| Acceptance / behavioral plausibility | REDESIGN | Distinct estimation layer after bilateral evaluation; not a substitute for utility. |
| Opportunity Engine | RETAIN / REDESIGN | Pure search/optimization consumer of authoritative decision APIs. |
| Analytics Terminal | RETAIN / REDESIGN | Read-only analytics/API client of shared authoritative outputs. |
| Trade reports | RETAIN / REDESIGN | Presentation from structured decision schema; no hidden math. |
| What-If / counterfactuals | RETAIN | Consume state transitions and authoritative forecast/value/simulation services. |
| Draft Intelligence | RETAIN / REDESIGN | Shared pick/player forecast and decision foundations. |
| Breakout/Sleeper analysis | INVESTIGATE | Preserve useful capability but rebuild atop forecast evidence rather than isolated heuristic scoring. |
| Hard-coded empirical coefficients | RETIRE as a category | Replace with governed parameter objects, structural derivations, or explicit bounded priors. |
| Duplicated specialist adjustments | RETIRE | One authoritative path per real-world effect. |
| League-specific assumptions embedded in core | RETIRE | League rules/configuration become first-class input. |
| Sleeper-specific domain objects | RETIRE | Sleeper becomes a provider adapter. |
| Legacy output parity requirement | RETIRE | NEXT differences are judged by evidence and coherence, not sameness. |

This is a starting inventory, not a final audit. NEXT-0 will expand it by inspecting the legacy repository and mapping authoritative concepts, tests, data dependencies, and known failure modes.
