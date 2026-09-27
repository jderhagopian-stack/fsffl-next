# FSFFL NEXT — Acceptance Gates

## Performance / intelligence lifecycle
Not complete until evidence demonstrates:
- durable last-good restoration;
- intentional mid-refresh restart behavior;
- stale-job reconciliation;
- truthful readiness state;
- no inappropriate automatic heavy refresh after restart;
- fresh 7/7 completion;
- atomic promotion;
- another restart surviving with the promoted last-good bundle intact;
- acceptable foreground latency during compute;
- Home, Franchise, and Market populated with governed evidence for the correct active league;
- no cross-league intelligence contamination.

Current status: **ACTIVE — MARKET FOREGROUND LATENCY ONLY.**

Evidence already satisfied for the existing FSFFL Dynasty incident:
- PR #222 fixes terminal failed/interrupted last-good restoration, same-league state-only demotion, restored-readiness precedence, and the mobile Refresh Intelligence grid/button;
- PR #226 is live on Render at `50614b1deeeccfe61c7b4fe3acc46111f7ad23cc`;
- production startup at 2026-09-25T13:52:35Z restored state `203227df...` with Forecast/Simulation/Value all present and `complete=True`;
- a second production restart at 2026-09-25T14:39:09Z restored the same complete bundle again;
- no automatic heavy intelligence job launched after either restart;
- PR #227 adds the interrupted-refresh restore regression and is merged/test-green;
- PR #235 / merge `3c252aed...` is live through Render deploy `dep-dar9kg142hec73dglcq0`; startup restored `jimmygoodjob` state `203227df...` with Forecast/Simulation/Value complete, no automatic heavy intelligence job and no startup errors;
- PR #235 removes request-local redundant Market input construction only. Repository-wide CI, PR164 corrective regression, and Live Forecast corrective trace are green, so PR #232 candidate admission, strategic-hypothesis, eight-path bilateral-screen, dominance/diversity, For You, and zero-broad-Simulation tests remain satisfied.

The jimmygoodjob last-good restoration evidence above is retained and must not regress. The separate Hodor/app-wide lifecycle corrective is now complete: PR #242 closed the Performance-owned State/lifecycle behavior, and Forecast PR #244/#245 subsequently populated durable shared Forecast + current Value while truthfully leaving Simulation absent under partial Forecast authority. Final Hodor restart evidence on Render shows `forecast=True simulation=False value=True complete=False` for State `d28de4cc...`.

Still open before Performance is complete:
- improve cold/focused Market foreground latency without weakening accepted Market discovery, Decision-screen, Forecast, or Simulation-authority semantics;
- preserve already accepted mobile lifecycle/state communication behavior.

The authenticated current-beta Market pass measured ~44.1s internal/~44.9s hosted cold automatic discovery and focused Target Player requests at ~31.8s, ~41.4s and ~47.8s, while a warm full workspace was ~0.137s. Foreground responsiveness therefore remains failed; CI or cache-hit evidence alone is insufficient.

## Forecast K/DST research
**Status: COMPLETE — RESEARCH / 2026 LATE-START PLAN READY.**

Research acceptance is satisfied by:
- `docs/operations/workstreams/RESEARCH.md`
- architecture: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`
- empirical/source closeout: `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_CLOSEOUT.md`
- 2026 late-start plan: `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`
- current-date source ledger: `artifacts/research/k_dst_late_start_exception_20260925/SOURCE_ACQUISITION_LEDGER.json`
- bounded empirical uncertainty results: `artifacts/research/k_dst_late_start_exception_20260925/EMPIRICAL_UNCERTAINTY_CHECK.md`

The completed research establishes:
- K as an individual-player Forecast family and D/ST as a team-unit asset;
- rule-level source independence and active-rule completeness;
- a one-season-only 2026 current-date ROS baseline exception with exact provenance and no backdating;
- explicit separation between current-forward 2026 authority and unavailable preseason comparison;
- subject-row source health against the real remaining NFL schedule;
- bounded empirical K and D/ST uncertainty measurements on explicit reduced scoring fingerprints;
- one current exact-capability provider candidate for Hodor-style 60+ K scoring and distributional D/ST PA tiers;
- no second public independent source yet proving those same hard coordinates;
- no Hodor-total uncertainty promotion from reduced fingerprints;
- no 2027+ late-start fallback.

No K/DST production coefficient or model authority is promoted merely by this research completion.

## New-league Forecast bootstrap research
**Status: COMPLETE — RESEARCH.**

The contract defines governed behavior for a league first connected after preseason:
- use an immutable league-agnostic annual raw Forecast snapshot when it exists;
- otherwise permit only an evidence-preserving migration of genuinely retained point-in-time raw Forecast evidence;
- preserve original timestamps, source identity, hashes, and lineage;
- do not refetch current pages and backdate them as preseason;
- fail closed on target scoring rules not supported by the retained raw evidence;
- when qualifying preseason evidence does not exist, surface preseason evidence as unavailable while permitting separately authoritative current-forward Forecast where valid.

## Forecast K/DST implementation gate
**Status: SHARED-FORECAST / PARTIAL-COVERAGE ACCEPTED — FULL K/DST AUTHORITY EXTERNALLY BLOCKED.**

PR #215 merged at `407c1bf85e5dc75f92b9906719f82bcd11d97c31` and established the base evidence-independent K/DST contract. PR #233 merged at `79c1f0c0aa094e4b1e3f6aa41eacd08c6bf1d6e8` and satisfies the first Management-authorized 2026 late-start implementation contract. PR #237 merged at `33b969b04180893f7e582c0ebd76c54bea81961d` and implements the second bounded private-beta exception: provisional current-ROS K/DST may expose only governed supported coordinates, with unsupported coordinates omitted and explicit partial-rule/provisional authority. Value/Simulation/Team Utility/Decision/Search may not silently consume it as full Forecast truth.


PR #244 merged at `edb9c0f9a1ccea4250761c63f65694d449c2d285` and restores the shared league-agnostic Forecast boundary. PR #245 merged at `7ad0d5ce4be038a2615433467227cdcfd3da85a4` and completes generic Sleeper acceptance plus truthful partial-authority lifecycle messaging. Final head `342f8c8e0ec4b0c8b1ffb5695abaf81ed98cb518` passed 1,620 full-suite tests plus all configured focused Forecast/Home/Atlas validations.

Production acceptance is satisfied for the corrective:
- Hodor no longer fails Forecast because its scoring includes unsupported coordinates;
- production emitted 330 explicit partial player-scoring outputs;
- Simulation was not promoted and reported `partial_player_scoring_coordinates_present` + `separate_k_dst_forecast_authority_required`;
- current Value became available;
- final Render deploy `dep-daredcl9fdbs7398s55g` restored Hodor State `d28de4cc...` with `forecast=True simulation=False value=True complete=False`;
- deterministic tests prove the same behavior across unrelated synthetic Sleeper league identities and materially different scoring profiles.

See `artifacts/implementation/hodor_shared_forecast_20260925/IMPLEMENTATION_HANDOFF.md`.

PR #238's exact-state safety hardening is already present on current main; the stale PR was closed unmerged after its six non-test implementation files were verified byte-identical to main.

Accepted code-level requirements already include:
- canonical K and D/ST subject identity;
- active-rule-complete scoring contracts;
- rule-level source-independence contracts;
- exact/derived kicker coverage without heuristic 50+ splitting;
- distributional D/ST bucket-scoring contract;
- deterministic K/DST realized-outcome and non-promoting calibration harnesses;
- immutable annual raw-snapshot replay;
- regression-clean no-K/no-DST behavior.

Management's 2026 exception changes the remaining acceptance gate:

### Cleared for current-forward 2026
- a K/DST baseline no longer needs pre-Week-1 provenance;
- a current-date ROS artifact may be acquired in 2026 if its real capture time, horizon, provenance and source-health are preserved;
- missing 2026 preseason K/DST evidence does **not** by itself block current-forward Forecast.

### Still unavailable
- any 2026 K/DST preseason comparison that lacks authentic pre-Week-1 evidence;
- the late-start artifact may never satisfy or masquerade as the annual preseason artifact.

### Empirical uncertainty evidence now available
Research has measured bounded reduced-fingerprint evidence:
- K season relative RMSE `0.3841884793`; weekly CV `0.5223274618`;
- D/ST sacks+INT season relative RMSE `0.2140283312`; weekly CV `0.6381941339`.

These are **research measurements only**. They are not accepted Hodor-total uncertainty coefficients because the fitted fingerprints exclude active Hodor coordinates.

### Current-forward Hodor blockers
Full-production K/DST authority remains unaccepted until evidence demonstrates:
- rights-cleared source access for the actual deployed provider set;
- >=2 independent healthy sources for each required subject/metric/horizon group;
- K: live validation of an exact 60+ evidence path plus a second independent 60+ source;
- D/ST: live validation of distributional PA-tier evidence plus a second independent PA-distribution source and remaining rare-event two-source coverage;
- target-compatible K and D/ST uncertainty promotion with explicit scoring-fingerprint compatibility;
- downstream Value/Simulation/Decision do not invent missing Forecast truth;
- successful new-league lifecycle acceptance under truthful downstream authority semantics.

These full-authority blockers do **not** erase the distinct 2026 provisional tier created by PR #237. Where qualifying rights-cleared current ROS evidence exists, Presentation/readiness/analytics may expose provisional K/DST with its omitted-coordinate and uncertainty limitations attached; downstream full-authority consumers remain blocked.

Already satisfied in PR #233:
- schedule-aware row freshness quarantines stale post-game ROS rows rather than backdating or heuristically adjusting them;
- the dedicated late-start artifact is hard-rejected outside 2026;
- research-only provider evidence and zero-uncertainty states cannot acquire production authority.

JerryGM is one technically exact-capability current ROS candidate:
- its docs support 60+ K custom scoring;
- its D/ST model exposes a PA spread and expected custom PA-tier value;
- its current ROS path is schedule-aware.
It remains an **external-access/rights candidate**, not production authority, until a live payload is validated and written usage rights permit FSFFL's derived multi-source Forecast use.

The controlling Research plan is:
`artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`.

## League-agnostic scoring coverage research
**Status: COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY.**

Research acceptance is satisfied by:
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/PLATFORM_COVERAGE_MATRIX.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/PRIMARY_SOURCE_LEDGER.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/GAP_ANALYSIS.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/IMPLEMENTATION_HANDOFF.md`

The completed audit demonstrates:
- documented major-platform defaults/custom scoring were researched without treating configurability as prevalence;
- a provider-neutral coordinate registry and rule-semantics model are defined;
- current FSFFL State/Forecast/scoring/provider/history gaps are explicitly mapped;
- nonlinear rules are separated from scalar-mean scoring;
- IDP is identified as a distinct subject-family expansion;
- provider raw-field preservation and historical replay requirements are defined;
- FULL/PARTIAL/UNSUPPORTED capability semantics and reason codes are defined;
- deterministic cross-platform fixtures are specified;
- implementation is staged without promoting production authority.

## Scoring coverage Stage 0/1 implementation gate
**Status: MANAGEMENT GATE — NOT AUTHORIZED BY RESEARCH COMPLETION.**

If Management authorizes implementation, Stage 0/1 is accepted only when evidence demonstrates:
- canonical registry/rule/capability contracts are versioned;
- raw platform scoring rules remain preserved alongside compiled mappings;
- current FSFFL scoring outputs are regression-identical through the compatibility lane;
- unknown/custom rules survive import and become explicit UNSUPPORTED rather than disappearing;
- position predicates, thresholds, stacking and semantic-profile fields are representable even when Forecast evidence is not yet available;
- rights-permitted provider raw numeric fields can be retained before canonical reduction;
- an unmapped provider field can be preserved without acquiring scoring authority;
- PARTIAL capability never publishes an incomplete authoritative fantasy-point total;
- no new production Forecast metric, provider authority, uncertainty coefficient, IDP support, or nonlinear model is promoted by Stage 0/1.


## Forecast FUMBLES_LOST authority gate
**Status: RESEARCH ACCEPTED — FIRST-PARTY MODEL READY FOR IMPLEMENTATION / PRODUCTION ACCEPTANCE.**

Management superseded the external-provider-permission critical path with the first-party Forecast-model directive.

Research acceptance is satisfied by:
- `artifacts/research/fumbles_lost_first_party_model_20260926/MODEL_SPEC.md`;
- `artifacts/research/fumbles_lost_first_party_model_20260926/CURRENT_INPUT_ASSESSMENT.md`;
- `artifacts/research/fumbles_lost_first_party_model_20260926/PRODUCTION_READINESS_HANDOFF.md`;
- machine-readable OOT validation and shadows in the same directory.

Accepted Research model:
`next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`.

Evidence:
- exact lost-fumble semantics only;
- chronological OOT folds 2023/2024/2025;
- combined primary OOT n=1,599;
- RMSE 0.8105 vs omission 1.0425 and position-game baseline 1.0475;
- bias +0.0509;
- zero-calibration gap 0.0347;
- current identity coverage 327/335 = 97.61%;
- non-zero position and cold-start residual uncertainty floors;
- model/features/gates frozen before 2026 named-player shadow inspection;
- no unrelated offense coordinate rebased.

Production acceptance is **not** satisfied merely by Research. Forecast/Product Implementation must demonstrate:
1. exact lost-fumble target semantics; total fumbles cannot substitute;
2. strict prior-season training and canonical completed-week current cutoff;
3. frozen 2026 scalar `0.6158756078393594` reproduced from governed pseudo-current evidence;
4. current input semantics exactly match the accepted opportunity definitions;
5. non-zero uncertainty floors and explicit degraded identity/cold-start tiers;
6. current State cutoff mismatch invalidates the model supplement;
7. the supplement is overlaid only into current player scoring;
8. retained preseason/ordinary offense raw Forecast content and identity remain unchanged;
9. no current first-party output is visible to an earlier PIT cutoff or 2026 preseason comparison;
10. missing/ambiguous model evidence never becomes a silent zero;
11. current FSFFL rebuild reaches legitimate full player-scoring authority before Simulation promotion;
12. existing Hodor/other-league partial-authority behavior does not regress.

Existing PR #253/#255 supplement plumbing remains the intended integration seam.

The external JerryGM + LineupExperts route remains fallback/benchmark only. It is no longer an acceptance prerequisite for the first-party path.

The auxiliary single-source tier remains irrelevant because this is a Forecast-owned empirical model, not a one-provider authority exception.


## Intrinsic cell-specific long-horizon Research gate
**Status: MANAGEMENT GATE — ROUTING/SHRINKAGE STUDY COMPLETE / NO PRODUCTION AUTHORITY.**

This gate supersedes the prior all-20-cell fallback interpretation.

Research conclusion:
- general Y4-Y7 policy: **soft position × horizon shrinkage** across development-qualified candidates;
- exact repeated-validation support: **QB Y4, WR Y4, QB Y6**;
- remaining 13 Y4-Y7 cells: **soft shrinkage with explicit uncertainty**, not hard exact route authority;
- Y8 QB/RB/WR/TE: **coarse/uncertain only** because only two qualifying outer origins exist;
- incumbent `forecast10 + two_part_ridge`: comparator, not blanket authority;
- old 75/25 architecture: comparison only; its QB Y8 failure remains valid evidence.

Rolling validation:
- soft shrinkage RMSE **43.20** vs incumbent **45.64**;
- tail RMSE **113.34** vs **134.77**;
- Spearman **0.5067** vs **0.4942**;
- 15/20 cells better than baseline composite;
- soft shrinkage worst-cell RMSE ratio vs baseline **1.074×**, versus **1.311×** for the rejected blanket architecture.

Required trajectory audit:
- target-horizon age and experience are not interchangeable with base age;
- QB shows stable nonlinear target-age/exposure benefit through Y7;
- RB accumulated workload adds mostly survival/relevance information;
- WR cumulative workload does not improve conditional production;
- TE requires nonlinear interactions and is more era-sensitive;
- no universal age penalty, youth bonus, or workload-wear coefficient is accepted.

No second untouched Y8 holdout exists. The repeated rolling evidence must not be represented as one.

Before any Y4+ production authority is considered, Management must separately authorize and accept:
1. production implementation of the chosen shrinkage/candidate contract;
2. live PIT feature coverage and deterministic route construction;
3. residual/model uncertainty presentation for non-exact cells;
4. a governed coarse/deep-horizon semantic for Y8;
5. cumulative cross-horizon covariance/scenario semantics if cumulative cardinal values are exposed;
6. exact H3 non-regression and Shapley/economic integration parity;
7. no Market/Owner/Team Utility leakage or hidden master score.

Durable handoff:
`artifacts/research/intrinsic_cell_routing_y4_y8_20260926/MANAGEMENT_HANDOFF.md`.

No Y4-Y8 production implementation is authorized.


## Current football-state Forecast update Research gate
**Status: MANAGEMENT GATE — NARROW FORECAST CONTRACT SUPPORTED / NO PRODUCTION AUTHORITY.**

Research does **not** accept a broad event-rich H1-H3 updater.

Accepted Research conclusions:
- football-state events trigger Forecast reevaluation;
- H1 must separate remaining-season availability from conditional active production;
- when a governed current ROS Forecast is authoritative, it owns H1 and no additive event haircut may be applied;
- temporary injury does not receive a generic H2/H3 penalty;
- provider-unavailable fallback must not manufacture a generic event multiplier;
- release/cut may be represented only as a coarse H3 attachment/survival-risk state based on the current evidence.

Current provider capture is not accepted for broad production H1:
- exact two-source standard scoring: 54 players;
- source deployment rights remain uncleared.

Before a production current-football-state updater is promoted, Management must separately accept:
1. an authoritative current H1 source/availability path with deployment rights and governed exact scoring;
2. explicit separation of availability, conditional active production, role and future survival;
3. the no-double-counting guard against provider ROS;
4. current PIT identity/provenance and event-trigger semantics;
5. Forecast output identity/version invalidation of dependent Intrinsic;
6. fail-closed behavior when current evidence is unavailable/ambiguous;
7. any release/cut H3 state as coarse unless a stronger dedicated validation supports cardinal precision.

No direct Intrinsic injury/transaction/role penalty is authorized.

Durable handoff:
`artifacts/research/current_football_state_h3_20260926/RECOMMENDED_FORECAST_CONTRACT.md`.

## Product principle
Do not make a red gate green by weakening model authority, fabricating projections, backdating evidence, or hiding unsupported assets in Presentation.


## Market / Trade Discovery architecture review
**Status: COMPLETE — MANAGEMENT ACCEPTED.**

Implementation-ready handoff:
- `docs/operations/workstreams/MARKET_DISCOVERY.md`
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

Architecture review evidence demonstrates:
- the repeated-neighborhood failure mechanism in the current package-row-first Search;
- why additive Cardinal closeness is insufficient before Decision-owned package economics;
- why current sparse bilateral enrichment cannot support a multi-card high-signal feed;
- how OpportunityHypothesis → MarketOpportunity → CandidatePath separates strategic attention from package variants;
- how existing Decision primitives can supply bounded pre-Simulation screening without fabricated acceptance probability;
- how family clustering, dominance pruning, and diversity selection prevent repeated target neighborhoods from crowding For You;
- why exact changed-state Simulation remains downstream of a selected transaction;
- why global 7/7 and lazy all-player Intrinsic readiness are different contracts;
- how Player Board / Free Agents can render partial governed evidence without weakening fail-closed authority;
- a deterministic fixture/test matrix including repeated Gibbs neighborhoods and extreme Superflex package shapes;
- a bounded implementation/migration sequence.

Management accepted the architecture on 2026-09-25 and authorized the bounded implementation executed in PR #220.

## Market implementation acceptance gate
**Status: CURRENT-BETA CORRECTIVE IMPLEMENTATION SATISFIED NON-PHYSICALLY — PHYSICAL IPHONE / SAFARI GATE NEXT.**

PR #240 is merged at `7b7f44ef0b3bf22008d80a3363aec1e6ce6f19d9` and live on Render as `dep-darb4lid0e5s73e2nnkg`, static generation `20260925-market-beta-corrective2`.

Acceptance evidence now includes:
- competitive posture materially constrains early target admission from governed age/season-Forecast evidence where available instead of remaining order-only;
- deterministic fixtures demonstrate appropriate Win-now/Rebuild divergence and fail-open overlap when evidence is missing;
- selector changes are configuration-only and cannot automatically launch focused Search;
- **Find opportunities** is the explicit expensive-work boundary with visible running/stale/completed state and response-race guards;
- focused zeroes expose where the submitted neighborhood exhausted, with candidate/admission/package/economic/family/preliminary-screen/dominance/final counts;
- the eight-path preliminary Decision budget is unchanged and does not truncate cheap Search exploration;
- broad discovery remains at zero exact changed-state Simulation calls;
- Forecast, Broad Market and FSFFL Intrinsic availability are independent, with per-player reasons and Intrinsic build/coordinate diagnostics;
- mobile Board/safe-area/Free Agent/Player Intelligence corrective behavior remains covered;
- full CI, all configured focused product regressions and live Forecast trace passed.

Production deployment is healthy with no application errors. The process currently restores the separate Hodor/new-league Performance context with derived intelligence incomplete, so no authenticated PR #240 focused/value-lens request has yet exercised the new production diagnostics.

**Remaining acceptance:** repeat physical iPhone/Safari Market validation on a context with sufficient governed evidence, followed by inspection of the emitted focus/value-lens telemetry. Do not weaken Market or lifecycle authority if Hodor remains incomplete.

## Layered product promotion gate
No product workstream may collapse multiple acceptance layers into one inferred success.

Required layers where applicable:
1. **model/research authority** — governed evidence and approved model/contract;
2. **core runtime** — correct State/Forecast/Simulation/Value identity and persistence;
3. **derived capability** — Intrinsic/future forecast/analytics consumers successfully materialize under the exact production composition;
4. **hosted endpoint** — real deployed API route succeeds for the target league/user/State;
5. **rendered surface** — the production client consumes the endpoint correctly;
6. **physical target** — required iPhone/Safari or other Management target behaves correctly;
7. **readiness truth** — shell status matches actual supported capabilities and freshness.

A passing lower layer does not promote higher layers. In particular, Forecast/Simulation/Value core readiness does not imply Intrinsic, League Atlas, Player Intelligence or Market surface readiness.

Promotion to a dependent workstream requires direct evidence for every layer that dependent work assumes.

## Forecast model-replaceability architecture gate
A promoted Forecast model is not fully accepted if its active production adapter depends on superseded model-specific orchestration in a way that can create divergent fixes, hidden population assumptions, or downstream coupling.

Acceptance requires:
- reusable inherited mathematical primitives are explicitly named/versioned and exposed through model-neutral boundaries;
- active model orchestration is owned by the active model/provider adapter;
- downstream consumers depend on stable Forecast contracts rather than prior-model internals;
- a subject/population rule has one authoritative implementation path;
- regression evidence proves the active provider can be replaced without requiring downstream model-specific changes.

Validated numerical reuse is allowed. Hidden implementation inheritance is not.

## Player Intelligence history memory / beta-availability gate
**Status: CODE ACCEPTED + EXACT DEPLOY LIVE — HOSTED LOAD / PHYSICAL ACCEPTANCE BLOCKED.**

PR #267 merge: `d737012079345768ef5cfd19debff97e0ede1bba`.
Exact Render deploy: `dep-das4k27avr4c73909lsg`.
Deterministic evidence: 1,704 full-suite tests plus all configured focused validations green.

Implementation acceptance requires and now proves:
- no concurrent multi-season PI career materialization;
- no unbounded full-population season cache retained by Player History;
- one-player season extraction before transformed materialization;
- durable player-season retrieval and durable final-career reuse;
- unchanged HTTP 202/loading semantics and request coalescing.

Production promotion is **not complete** until one real authenticated PI history build on the live
512 MB instance proves:
- 202 → ready/200 without 502/503;
- same instance survives;
- memory remains safely below the 536,870,900-byte limit and materially below the prior failure curve;
- repeat open reuses the persisted career result without recreating the build spike;
- physical iPhone and iPad Player Intelligence render/interaction succeeds.

This gate is independent of Intrinsic authority and State-first persistence.

## Private-beta runtime architecture / availability gate — 2026-09-27
**Status: OPEN — STRUCTURAL CORRECTIVE REQUIRED.**

Current main is not accepted despite PR #270 hosted synthetic acceptance. Physical iPhone evidence and hosted telemetry showed false-green readiness, PI/League failures, HTTP 429 recovery failure, and a memory-limit-consistent process recycle.

Promotion requires the exact combined cold-wake/user-journey acceptance defined in `docs/operations/workstreams/IMPLEMENTATION.md`, including:
- regression comparison against the last demonstrably usable PR #235-era FSFFL runtime behavior;
- one bounded authoritative heavy working set plus lightweight/lazy last-good presentation;
- bounded/coalesced heavy-job concurrency;
- restore-first startup before automatic heavy refresh;
- single cross-surface readiness truth;
- crash-safe persisted context restoration;
- peak RSS <= ~429 MB on the current 536,870,900-byte service limit (>=20% headroom);
- zero process recycle, 5xx, recovery-induced 429, blank canonical roster/state, or false-green readiness through the complete journey;
- repeat/reuse evidence proving durable artifacts reduce subsequent work.

A page-specific hotfix, one green endpoint, CI-only success, or a synthetic runner that does not reproduce browser-driven overlap is insufficient for promotion.


### 2026-09-27 physical changed-State evidence — gate remains OPEN
PR #271 is not promoted. Physical iPhone/Safari evidence showed that automatic Sleeper State reconciliation can advance canonical State and cause previously usable derived presentation to disappear into rebuilding/unavailable rather than remain available as a clearly stale/as-of last-good read model.

The same window showed ~411 MB observed peak RSS: below the <=~429 MB ceiling but too close to treat as comfortable headroom, and the product continuity requirement failed regardless.

Additional acceptance requirement is now explicit:
- after an automatic State advance, every primary surface must continue serving a compact persisted last-good presentation until the new exact-State capability is ready;
- Market navigation must not be blamed for a State transition that was initiated by background refresh;
- the hosted acceptance harness itself must deploy/run successfully; an update timeout cannot count as evidence.

The gate remains OPEN.


## Research model-selection gate — symmetric evidence, no incumbent privilege — 2026-09-27
Research promotion gates must not privilege the currently used or first-studied model solely because of chronology.

- Absolute adequacy/safety gates remain binding.
- Head-to-head model comparisons must be symmetric.
- A challenger does not need to exceed an incumbent by an arbitrary replacement margin unless that margin is tied to a predeclared practical cost/utility threshold that would apply equally in reverse.
- If two candidates are within uncertainty or practically indistinguishable, record that explicitly; do not default the scientific conclusion to the incumbent.
- Predictive authority should be decided by the best-supported representation of the actual target and product-relevant downstream quantities.
- Operational switching cost, migration risk, compute, or maintainability may justify temporarily retaining an existing production model, but that is a separate implementation/product gate and must not be represented as Research superiority.

Previously frozen experiments remain historically valid; this rule governs their interpretation and all future model-family comparisons.


## Dual-Intrinsic / long-horizon Forecast promotion gate — 2026-09-27
Management has accepted the target architecture but **has not yet promoted Long-Term Intrinsic to production**.

Promotion requires:
- continuous governed Y4-Y7 Forecast inputs; no Y5-only shortcut;
- exact-policy authority only where Research earned it and explicit model-authority envelopes elsewhere;
- Y8 excluded from precise cardinal Long-Term Intrinsic while evidence remains coarse;
- a frozen Research-defined Long-Term Intrinsic economic consumer with no arbitrary horizon weights;
- clear separation of Current Intrinsic (Y1-Y3) and Long-Term Intrinsic (Y4-Y7);
- within-model and between-model uncertainty represented separately;
- no hidden Market/Team Utility or contender/rebuilder adjustment inside either intrinsic lens;
- scale semantics proven if both lenses use 0–10,000;
- downstream Market/Team Utility integration treated as a separate promotion layer;
- deterministic tests, exact model/version provenance, replay evidence, and physical product validation before presentation acceptance.

Until this gate is satisfied, production Current Intrinsic and deployed Y2/Y3 Forecast remain unchanged.


## Long-Term Intrinsic shadow implementation gate — authorized 2026-09-27
Status: **AUTHORIZED FOR SHADOW BUILD; NOT YET PRODUCT-AUTHORITATIVE.**

Before shadow merge/deploy:
- PR #278 runtime acceptance must complete without a new availability/latency blocker;
- Y4-Y7 Forecast authority materialization must preserve the frozen symmetric policy map exactly;
- full Long-Term Intrinsic consumer replay must match Research invariants;
- Current Intrinsic must remain byte/semantic unchanged;
- model-authority and within-model uncertainty must serialize separately;
- Y8 must not contribute cardinally;
- no Market/Team Utility/Decision inputs may enter the consumer;
- current-player full authority-envelope materialization must complete;
- resource/runtime/persistence behavior must be measured on beta constraints;
- league-agnostic lineup derivation must be covered.

Shadow acceptance does not itself authorize UI/Market promotion.


## Long-Term Intrinsic shadow sequencing clarification — 2026-09-27
The shadow gate remains defined, but execution is **paused** until the active runtime corrective reaches a permitted terminal state. No Long-Term Intrinsic implementation branch, merge, deploy or product promotion should proceed before that sequencing gate is reopened by Management.


## PR #278 hosted result — 2026-09-27 18:16 ET
Status: **FAILED / MATERIAL PARTIAL SUCCESS.**

Passes:
- cold PI retained compatible Y1/Y2/Y3 evidence;
- State/presentation reconciliation reached full/current;
- no stale surfaces after promotion;
- no process recycle, 5xx/429, or State loss in observed journey.

Fails:
- peak RSS 450,359,296 bytes exceeds the 429,496,720-byte engineering target;
- Market workspace build reached ~64.9s under concurrent acceptance work, so foreground responsiveness is not yet accepted.

Continue narrow corrective work; do not treat the internal RSS miss alone as an availability outage, but do not close the runtime gate while the combined latency/resource journey still fails.


## Foreground Market execution acceptance — 2026-09-27
Acceptance now requires:
- Market/Home/My Team/Product Context reads do not trigger full Search/Decision work;
- persisted/current or compatible last-good product reads remain responsive during heavy work;
- explicit Market search returns structural results without waiting for full bilateral enrichment;
- Decision enrichment is progressive and does not block the initial response;
- deep Simulation remains explicit;
- compatible PI history/Forecast is served before background reconciliation completes;
- no recycle, 5xx/429, or State loss in the ordinary journey;
- hard memory-limit safety is preserved.

The ~429.5 MB engineering RSS target is informative but is not, by itself, a product-availability failure.
