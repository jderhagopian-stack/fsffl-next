# FSFFL NEXT — Phase 3 Product Reconciliation

Status: **Phase 3 active — Intrinsic Value productized; commercial cold-path latency slice implemented for review**  
Roadmap authority: `docs/FSFFL_NEXT_PRODUCT_PRIORITIES.md`  
Original reconciliation starting `main`: `641378af5b4d9bb99eae5ec3aa4ee8cc70118d5b`  
Commercial-latency slice starting `main`: `72fbfd35a920fa38cea523ef0979735e4e1ceb56`  
Starting live Render SHA for both slices: `f38e2f029a0d9563986635012336434a3f9beb63`

This document records actual product state against the canonical roadmap. It does not replace or silently rewrite that roadmap.

## Reconciled deployment state

At the original reconciliation, GitHub `main` contained the merged FSFFL Intrinsic Value v1 work from PR #133 while the private-beta Render service was still serving `f38e2f...`. PR #134 subsequently productized Intrinsic Value and merged as `72fbfd35...`.

At the start of the commercial-latency slice, `main` was exactly `72fbfd35...`, confirming PR #134 was merged. Render was still serving `f38e2f...` because the private-beta service is configured to deploy the older `next-8-product-layer` branch rather than `main`. That deployment lag is operationally important but is not repaired by silently changing deployment configuration inside this product-performance PR.

Three states therefore remain distinct:

1. **merged to main** — repository-authoritative behavior;
2. **available in the current live beta** — dependent on the Render branch/deploy configuration;
3. **customer-facing/productized** — presentation exists and is understandable when that repository state is deployed.

Open PR overlap at the start of the latency slice:

- PR #131 — research-only multi-year intrinsic work; draft/unmerged; no production authority and no overlap with this performance slice.
- PR #132 — roadmap documentation alignment; open and based on older `main`; no product implementation overlap.
- no parallel performance PR.

## Phase 3 surface matrix

| Surface | Current status | What exists today | Exact unfinished gap | Gap type | Phase 3 exit impact |
| --- | --- | --- | --- | --- | --- |
| Home — “What should I care about right now?” | **MOSTLY COMPLETE** | Scan-first league/team attention view, competitive state, expected wins/playoff outlook, opportunity handoff, league comparison | Useful beta discoveries still need a durable product-learning loop | Product learning | Medium |
| Franchise — “What is actually driving my franchise?” | **MOSTLY COMPLETE** | Strong diagnosis plus the PR #134 Value Lens that clearly separates Broad Market, FSFFL Intrinsic, unavailable League Market and Team Utility | Validate with real beta use after deployment | Beta validation | Medium |
| League — “How do these teams differ?” | **MOSTLY COMPLETE** | League comparison, team structure, positional map, age/depth/future-capital context | League Market Value is not production-ready | Backend evidence | Medium |
| Opportunities / Trade Finder — “Where is there something worth doing?” | **MOSTLY COMPLETE after latency slice** | Market Focus, opportunity detail, feasibility, credible package handoff, exact Search caching, and now a search-only quick view before bounded Decision enrichment | Fresh structural Search itself still determines the quick-view floor; Intrinsic-vs-Market disagreement is not yet a discovery lens | Performance / product intelligence | High |
| Trade Center — “What happens if I make this deal?” | **MOSTLY COMPLETE after latency slice** | Immediate package-economics quick view, existing pre-Simulation bilateral roster analysis, unchanged 50k Simulation, quick/deep counter paths | Fresh 50k Simulation still takes about 85s when no exact reusable artifact exists | Performance | **High** |
| Behavioral Intelligence — “How should I understand and approach this owner?” | **MOSTLY COMPLETE** | Customer-facing observed owner history, trade shapes, position flows, counterparties, provenance; unsupported inference remains gated | Context-controlled owner preference / calibrated acceptance remain evidence-blocked | Evidence | Medium |
| Team/Owner-Adjusted Value | **BLOCKED** | Team Utility is separate and Decision uses franchise context | No governed owner-adjusted asset coordinate is production-ready | Evidence | Medium |
| Performance / commercial latency | **PARTIAL → materially improved delivery contract** | Exact caches, durable Simulation reuse, quick frontier, progressive Market/Trade delivery, duplicate exact Simulation coalescing, phase instrumentation | Raw fresh 50k compute remains the dominant deep-analysis blocker | Performance | **High** |

## Intrinsic Value productization

PR #134 closed the primary customer-facing Intrinsic gap by adding a Franchise **Value Lens**. It teaches the four-coordinate architecture in plain language:

- **Broad Market Value** — what the wider dynasty market prices;
- **FSFFL Intrinsic Value** — what FSFFL’s multi-year football economics imply above lineup replacement;
- **League Market Value** — explicitly unavailable until governed league-specific pricing exists;
- **Team Utility** — separate franchise/context value.

The lens lazily requests governed Intrinsic evidence, shows confidence and provenance secondarily, compares Market and Intrinsic only through percentile rank as a presentation aid, and treats disagreement as a reason to investigate rather than an automatic trade command.

## Commercial cold-path latency — measured starting state

Re-measured from the actual Render logs at the start of this slice:

- cold `/api/opportunities/workspace`: **15.037s**; underlying workspace build **14.910s**;
- exact repeated Market workspace: approximately **0.131–0.180s** end to end;
- `/api/trade-center/browser`: approximately **0.042–0.390s**;
- fresh `/api/trade-center/analyze`: approximately **13.245–13.269s**;
- fresh `/api/trade-center/simulate`: approximately **85.025s** for the unchanged 50,000-run changed-roster Simulation;
- exact repeated Simulation: approximately **1.227s**;
- historical deep frontier observations: approximately **315.845–331.544s**;
- fresh full Opportunity trade evaluation: approximately **83.849–91.752s**, versus approximately **1.404s** when reusable Simulation evidence was available.

These figures describe the live `f38e2f...` beta, not the unmerged latency branch.

## Bottleneck diagnosis

### Market

The cold Market endpoint was not waiting only on Search. `build_opportunity_workspace` generated the structural Search catalog and then synchronously performed one full bilateral pre-Simulation Trade Decision enrichment before returning the first workspace. The same bilateral analysis path independently measured near 13 seconds. Repeated Market was already fast because exact workspace and structural-catalog caches were effective.

### Trade Center

The pre-Simulation analysis combines legal changed State, package economics, mandatory cuts, lineup/position comparisons, four before/after franchise utility vectors, bilateral evaluation, decision shape and negotiation feasibility. It is authoritative but too expensive to be the first visible response.

### Simulation

Exact completed Simulation reuse was already strong, but two simultaneous cold requests for the same exact changed State could both miss before either completed and therefore launch duplicate 50,000-run work. Fresh Simulation itself remains the deepest compute cost.

## Progressive answer delivery contract

This slice does **not** create two competing truths.

### Market

1. **Quick view:** the same server-owned structural Search workspace with `bilateral_evaluation_limit=0`. It contains current canonical Search evidence and explicitly marks Decision enrichment as pending.
2. **Updated view:** the existing full workspace endpoint adds the same bounded bilateral Decision enrichment as before.
3. The quick and full workspaces share the exact structural Search catalog cache. The quick view can therefore populate the structural catalog once and the full follow-up reuses it rather than rebuilding the package universe.
4. Old results are discarded if league/team/state identity changes before completion.

### Trade Center

1. **Quick view:** canonical asset validation, legal changed-State application and existing governed package/market economics. It is labeled `partial_package_economics` and explicitly has no final disposition or competitive outcome authority.
2. **Roster analysis:** the existing `/api/trade-center/analyze` endpoint adds mandatory-cut, lineup, resilience and bilateral Decision evidence. It remains explicitly pre-Simulation.
3. **Full analysis:** the existing `/api/trade-center/simulate` path runs or exactly reuses the unchanged full 50,000-run Simulation and then produces Simulation-backed Decision/materiality/disposition evidence.
4. Quick failure does not fabricate deeper evidence; deeper failure leaves the already-valid quick evidence visible for its stated scope.
5. Every stage is guarded by current context + exact draft identity so an old request cannot overwrite a newer league, forecast state or draft.

## Exact reuse and concurrency behavior

Scenario reuse remains keyed on the exact changed LeagueState, exact Simulation-facing forecast fingerprint, loader/configuration identity and Simulation model contract. The new in-flight layer adds only one rule: two concurrent requests with the **same exact key** share the same authoritative running Simulation instead of launching duplicate 50,000-run work.

A changed State, changed forecast evidence, changed loader/configuration identity or otherwise different key still forces a separate authoritative run. No interpolation, reduced run count or approximate competitive result is introduced.

Additional phase instrumentation now records:

- quick Market total;
- quick Trade State validation and package economics;
- full Trade State validation, package economics, lineup/legality, roster Decision and finalization;
- Simulation key lookup, durable lookup, exact in-flight wait, 50k execution and persistence;
- post-trade Simulation preparation, Simulation/reuse and post-processing;
- total endpoint wall clock for both quick and full Market/Trade/frontier routes.

## Expected user-perceived effect before live deployment

The previous first Market payload included the approximately 13-second bilateral enrichment. The new first Market payload removes that enrichment from its critical path and returns after the same structural Search work only. Based on the observed 15.037s Market total and roughly 13.25s independently measured bilateral analysis, this targets a low-single-digit first useful Market response on the same class of workload. This is a component-based expectation, **not** a claimed live post-change measurement; the PR branch is not the Render deployment branch.

Trade Center likewise no longer requires the approximately 13.25s pre-Simulation analysis before showing anything useful. Its first response is limited to changed-State validation and package economics, while the existing roster analysis follows and the unchanged 50k Simulation then enriches it. The full fresh-analysis wall clock is not expected to become 85 seconds faster; instead useful governed evidence appears materially before the deep run finishes.

Fresh Simulation runtime itself is intentionally not claimed improved absent hosted post-deploy measurement. The concrete compute improvement in this slice is removal of duplicate identical concurrent 50k runs plus clearer phase timing for the next optimization decision.

## Mobile / progressive-state design

At <=680px:

- quick Trade package cards stack to one column;
- status/progress rows stack rather than forcing horizontal compression;
- the first governed answer stays above deeper evidence and does not require scrolling through a large progress dashboard;
- quick Market uses a single compact progress row;
- context changes invalidate old progressive responses before they can redraw the current analysis.

Copy is deliberately customer-facing: **Quick view ready**, **Full simulation running**, **Updated analysis ready**, rather than implementation terminology.

## What remains after the latency slice

Phase 3 is still not complete.

1. **Fresh 50,000-run Simulation compute** remains the primary deep-analysis latency blocker at roughly 85 seconds in the last live measurement. The new phase logs should be used after deployment to determine whether preparation, the core 50k execution, persistence or post-processing deserves the next bounded optimization. Do not reduce fidelity.
2. **Render deployment alignment** needs an explicit operational decision: the private beta currently deploys `next-8-product-layer`, so merged `main` work is not automatically reaching the beta.
3. **Intrinsic disagreement discovery beyond Franchise** remains a potentially useful Trade Finder product slice after latency behavior is validated.
4. **League Market Value** remains unavailable until governed evidence exists.
5. **Owner-adjusted value / calibrated proposal fit** remains blocked on appropriate point-in-time Behavioral evidence.
6. **Durable beta-learning record** remains a Phase 3 exit requirement.

## Recommended following Phase 3 slice

After this PR is merged and actually deployed, use the new hosted phase timings to run a **fresh 50k Simulation execution optimization** slice focused only on the dominant measured stage. Candidate techniques may include deterministic preprocessing reuse, unchanged-team distribution reuse or safe vectorization, but only if the phase evidence supports them and only with identical Simulation semantics and 50,000-run fidelity.

If hosted measurements instead show the quick Market structural Search path is still not low-single-digit, the next bounded performance step should target the structural candidate catalog itself rather than reintroducing Decision work into first paint.
