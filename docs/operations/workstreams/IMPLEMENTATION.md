# FSFFL NEXT — Forecast / Product Implementation

Updated: 2026-09-25

## State
**DIRECTIVE COMPLETE — HODOR SHARED-FORECAST POPULATION + PARTIAL-COVERAGE CORRECTIVE**

Management has superseded the prior blanket “external evidence blocks further implementation” stop for the current Hodor population issue. Full K/DST authority remains externally gated, but that gate may not collapse otherwise valid canonical Forecast coverage.

The governing decisions are now:
- one canonical league-agnostic player/stat Forecast truth; league scoring is a downstream transformation;
- valid governed forecastable coordinates remain usable even when some active scoring events are unsupported or inherently unforecastable;
- missing evidence must never silently become zero;
- bounded rare/special-event gaps may produce explicit PARTIAL / PROVISIONAL scored outputs with omitted-coordinate metadata and downstream authority limits;
- only a materially disqualifying missing coordinate may block the affected subject/consumer, not unrelated positions or the entire league;
- the Hodor Performance lifecycle corrective is complete at PR #242; Forecast/Product now owns the remaining Hodor population blocker.

### Current Hodor production evidence
The historical Hodor failure was `LiveForecastSourceHealthFailure: authoritative live ensemble found 0 qualifying independent full-season sources under Hodor scoring`. That league-wide Forecast failure is resolved.

PR #244 merged at `edb9c0f9a1ccea4250761c63f65694d449c2d285`. An authenticated production Hodor refresh then advanced through shared Forecast population rather than failing `BUILDING_FORECASTS`: 330 player-scoring outputs were explicitly partial, and Simulation was withheld with `partial_player_scoring_coordinates_present` plus `separate_k_dst_forecast_authority_required`. Current Value became available.

PR #245 merged at `7ad0d5ce4be038a2615433467227cdcfd3da85a4` after 1,620 full-suite tests and all configured focused workflows passed. Render deploy `dep-daredcl9fdbs7398s55g` is live on that exact merge. Its startup restored Hodor league `sleeper:1397623301961981952`, refreshed State `d28de4cca9d35faeb88446449ef09984cdb57c753ef835121d70101ca56b31cb`, with `forecast=True simulation=False value=True complete=False`. The partial-authority state therefore survives restart without promoting blocked Simulation.

Durable closeout:
- `artifacts/implementation/hodor_shared_forecast_20260925/IMPLEMENTATION_HANDOFF.md`

### Authorized corrective
Forecast Implementation must:
1. trace why league-specific Hodor scoring is rejecting or hiding otherwise valid shared canonical QB/RB/WR/TE statistical Forecast evidence;
2. restore the approved boundary: canonical football-stat Forecast is league-agnostic, and Hodor scoring is applied downstream without creating a duplicate league-specific projection database;
3. implement FULL / PARTIAL-PROVISIONAL / UNSUPPORTED behavior so supported coordinates populate even when bounded scoring components cannot credibly be forecasted;
4. ensure unsupported events are explicit omissions with reason/coverage metadata, never fabricated and never silently zeroed;
5. isolate materiality at the affected subject/consumer boundary rather than treating one unsupported coordinate as a total-league Forecast failure;
6. reconcile PR #238 onto current main and preserve exact league/state binding for provisional K/DST scored outputs;
7. trace the 2026 provisional K/DST path end-to-end and explain/repair why production currently has zero provisional artifacts wherever governed supported evidence is actually available;
8. keep genuinely unavailable K/DST components explicit while allowing independently valid offensive Forecasts and other supported projections to populate;
9. carry the corrective through tests, merge, Render deployment, and production Hodor validation before returning control.

Full K/DST authority still requires its existing external source/rights/exact-coordinate/uncertainty gates. This directive does not authorize fabricated 60+ FG frequency, nonlinear PA-bucket reconstruction from aggregate means, invented rare-event rates, invented source rights, or silent promotion of partial evidence into full Value/Simulation/Decision/Search authority.



### Generic Sleeper-league acceptance requirement
This corrective is architectural, not Hodor-specific. Production behavior must contain no special casing for Hodor, `jder52`, any known Sleeper league ID, or any known franchise ID.

Acceptance must prove that the same pipeline works when supplied an arbitrary valid Sleeper league identity/state:
- connect/select the league through the normal Sleeper path;
- preserve the league's actual scoring/rules/state identity;
- reuse canonical league-agnostic player/stat Forecast evidence;
- derive league-specific scored outputs from those rules;
- isolate K/DST or other unsupported subject/rule families without erasing unrelated valid Forecast;
- emit FULL / PARTIAL_PROVISIONAL / UNSUPPORTED / NOT_APPLICABLE from capability/evidence, not league-name or league-ID branches.

Hodor may remain a regression fixture because it exposed the defect, but Hodor-specific fixture names or expected outputs are not sufficient acceptance. Add deterministic coverage using arbitrary/synthetic league IDs and materially different scoring profiles. Existing Sleeper cross-league selection tests must remain green.

The intended product contract is: a user may enter/select any valid Sleeper league ID; FSFFL NEXT loads its State/roster and computes every intelligence layer that the league's rules and governed evidence support. Unsupported or unforecastable coordinates degrade only the affected capability and are reported explicitly rather than causing league-wide failure.

### Acceptance target
Production acceptance requires the correct Hodor league/state and roster plus supported canonical Forecasts populated from shared player/stat evidence, truthful FULL/PARTIAL/UNSUPPORTED coverage by affected subject/rule family, explicit omitted-coordinate reasons, and a precise residual blocker for any downstream capability that still cannot operate.

Do not reopen generic source Research merely because a bounded scoring event lacks a credible projection. Some scoring events may remain explicitly unforecastable; that is a coverage condition, not automatically a total Forecast failure.

Management accepted the completed K/DST + late-connect Research contract and authorized its bounded implementation. The base architecture remains authoritative:
- `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

Management's current implementation authority is:
- `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`
- `artifacts/implementation/k_dst_late_start_20260925/IMPLEMENTATION_HANDOFF.md`

Implementation PR **#215** is merged on canonical main at `407c1bf85e5dc75f92b9906719f82bcd11d97c31`.

Management-authorized late-start implementation PR **#233** is merged on canonical main at `79c1f0c0aa094e4b1e3f6aa41eacd08c6bf1d6e8`. Its reconciled head `1e9eb293c7029b0953c3ecec8353b8c2638ea35e` passed full CI, PR164 focused corrective regression, Live Forecast corrective trace, and Corrective live provider numerical trace before merge.

## Implemented in the active PR
### Stage 1 — contracts and scoring
- canonical NFL team identity/aliases shared across State and Forecast;
- K remains an individual-player Forecast family;
- D/ST has a canonical NFL team-season Forecast subject and player-shaped D/ST observations are rejected;
- K and D/ST raw metric contracts are explicit;
- rule-level source evidence carries an independence-group identity;
- K exact vs exact-derived coverage is explicit, including no 50+ heuristic split into 50–59 / 60+;
- D/ST linear event scoring is distinct from per-game distributional points/yards-allowed bucket scoring;
- team special-teams and player special-teams semantics remain separate;
- active missing `fum_lost` evidence fails closed rather than silently contributing zero;
- CBS no longer manufactures a zero fumble-loss projection when the provider column is absent;
- Sleeper rostered D/ST assets retain canonical team identity for the roster→Forecast team-unit boundary;
- unrostered Sleeper player enrichment includes K but does not reinterpret D/ST as a player Forecast subject.

### Stage 2 — non-promoting research harness
- deterministic nflverse-style K realized-outcome reconstruction;
- conservative directly observable D/ST realized-event reconstruction;
- explicit missing kick-distance completeness defects rather than guessed distance bands;
- non-promoting season-error fitting gated on at least two independent sources;
- weekly volatility fitting uses realized game scores rather than season-total / 17 shortcuts.

## Authority deliberately not promoted
The PR does **not** create or claim:
- live K/D/ST provider authority;
- a K or D/ST production uncertainty coefficient;
- a qualifying 2026 K/DST preseason baseline;
- current/post-opener data relabeled as preseason;
- annual-snapshot-v2 migration acceptance;
- K/DST Value, Simulation, Decision, Search, or Presentation truth;
- any weakening of the existing two-independent-source requirement.

## Acceptance validation
The first PR run correctly exposed historical synthetic fixtures that had relied on an implicit missing-`fum_lost` zero. Those fixtures were repaired by supplying explicit synthetic zero observations only where the fixture itself owns that evidence. Runtime/provider evidence remains fail-closed.

After reconciliation with concurrent Market operating-state changes, the final PR #215 head passed full CI, focused corrective regression, private-beta Intrinsic diagnostics, live Forecast corrective trace, and the governed live-provider quarantine trace, then merged to main.

Post-merge Stage 2 evidence recovery was also attempted. The result is persisted in `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`: no qualifying second historical independent K/DST PIT corpus was recovered, and candidate production sources remain rights/licensing gated.

## Remaining evidence gates after PR #233
The bounded implementation is complete. Production K/DST authority remains fail-closed until:
1. authorized live API/source access and deployable rights are available for an exact-capability provider path;
2. a second independent current ROS source proves the Hodor-specific K 60+ coordinate;
3. a second independent current ROS source proves D/ST remaining-game PA distribution plus the remaining rare-event coordinates;
4. target-compatible full-score K and D/ST uncertainty is empirically promoted under an exact scoring fingerprint;
5. only after Forecast authority is genuinely green, the new-league lifecycle is re-run for downstream acceptance.

The 2026 preseason comparison remains explicitly unavailable where authentic pre-Week-1 K/DST evidence does not exist. Missing preseason evidence is no longer a current-forward blocker.

These are external evidence/rights dependencies. They may not be bypassed with offense coefficients, one-source estimates, synthetic production values, zero uncertainty, average-based D/ST bucket reconstruction, or backdated current data.

## 2026 late-start exception implementation
Management superseded the prior blanket implementation stop with a bounded one-season-only 2026 current-date ROS authorization. PR #233 completed that evidence-independent implementation while preserving the remaining rights/exact-coordinate/uncertainty gates.

The merged implementation includes the dedicated non-preseason artifact, hard 2026 boundary, schedule-aware row quarantine, rights-aware independent-source coverage, K/DST ROS normalization, exact K algebraic transforms, explicit calibration fingerprints, deterministic replay/holdout diagnostics, and no-zero-uncertainty authority assessment.

The late-start artifact is not preseason authority. It is hard-disabled for 2027+.

## Corrective terminal state
The Hodor/shared-Forecast corrective is accepted and complete. Canonical raw player/stat Forecast is league-agnostic; scoring-family gaps now degrade only affected scored outputs/consumers; partial omissions are explicit; Simulation is gated separately; and the same behavior is regression-proven across unrelated synthetic Sleeper league identities and scoring profiles.

No further implementation is authorized merely to make Hodor fully scored. Full K/DST authority remains a distinct external-evidence dependency. Resume that authority program only when authorized API/source access or a newly supplied independent exact-capability source can materially clear a remaining gate. Do not substitute heuristics.

**DIRECTIVE COMPLETE — FORECAST / PRODUCT IMPLEMENTATION — HODOR SHARED-FORECAST / PARTIAL-COVERAGE CORRECTIVE**

Residual full K/DST authority: **BLOCKED — EXTERNAL SOURCE RIGHTS + SECOND-SOURCE EXACT COORDINATES + TARGET-COMPATIBLE UNCERTAINTY**


## Physical iPhone acceptance — Hodor partial-Forecast pass
**State: ACCEPTANCE FAILED — READINESS/PRESENTATION SEMANTICS CORRECTIVE REQUIRED**

Management physical-iPhone/Safari evidence after the Hodor shared-Forecast corrective shows materially improved lifecycle population but an internally inconsistent product state.

Observed:
- prior state showed Hodor / jder52 at 2/7 with an empty roster;
- current state shows Hodor / jder52 at 7/7 with “Core intelligence current” and a valid 16-player roster;
- Home simultaneously shows Position pressure point unavailable and Current Simulation unavailable;
- Franchise shows “Forecast / Simulation-derived fields are unavailable,” no position-strength evidence, and Not Classified;
- League Atlas standings/position-strength cells remain unavailable while the surface text still references 50,000 simulations using current standings, rosters and forecast evidence;
- Value Map shows Broad Market values for players where available but FSFFL Intrinsic remains unavailable;
- future-pick rows show Broad Market value unavailable.

Management acceptance interpretation:
1. The architectural correction is directionally successful: valid State/roster now survive and shared Forecast can populate without K/DST collapsing the entire league.
2. The green 7/7 “Core intelligence current” presentation is not acceptable when governed Simulation/position-strength/classification/Intrinsic outputs that the UI presents as core intelligence are unavailable.
3. Job/lifecycle completion must be distinguished from intelligence-capability readiness. “Completed” may truthfully mean the pipeline exhausted all authorized work and reached a stable partial-authority state; it must not automatically render as “7/7 Core intelligence current.”
4. The readiness UI must expose capability state, not just stage completion. Full vs partial/provisional vs unavailable must be explicit for Forecast, Simulation, Value/Intrinsic, and derived surfaces.
5. Surfaces must not display descriptive copy that implies unavailable analytics are present (for example “50,000 simulations using current standings, rosters and forecast evidence”) when Simulation is authority-blocked.
6. A valid arbitrary Sleeper league may legitimately reach a stable partial-authority state; that state is acceptable only if the UI accurately represents what is and is not available.
7. Hodor-specific behavior remains prohibited. The corrective must apply generically to any valid Sleeper league/state.

Required corrective:
- separate lifecycle/job completion from intelligence readiness;
- redefine the top readiness indicator so green/full status is earned only by the capabilities that the label claims are current;
- if retaining a 7-stage lifecycle counter, label it as lifecycle/build completion and separately show capability readiness;
- ensure Home/Franchise/League/Market copy and badges consume the same governed capability truth;
- preserve the existing partial-Forecast architecture and do not weaken K/DST/Simulation/Value authority merely to make the badge green;
- validate on Hodor plus arbitrary/synthetic Sleeper league IDs and at least one fully supported existing league;
- continue through tests, merge, Render deployment, and production physical-device-ready validation before returning control.

This is a product truth/acceptance issue, not permission to fabricate missing Simulation, Intrinsic, position-strength, or K/DST authority.


## Root-cause diagnosis — Hodor post-PR245 physical pass
Management traced the post-PR245 Hodor partial-authority state against production code and persisted Hodor State.

### 1. Ordinary player Forecasts are partial because active `fum_lost` scoring lacks raw Forecast evidence
The persisted Hodor scoring contract includes `fum_lost = -2` in addition to ordinary pass/rush/receive scoring. The current league-scoring bridge explicitly treats active FUMBLES_LOST as a standalone material coordinate: if it is scored and absent from a player's raw Forecast evidence, that player's fantasy-point total is emitted only as PARTIAL_PROVISIONAL rather than authoritative.

PR #245 production evidence reported `partial_players=330` and blocker `partial_player_scoring_coordinates_present`. Given Hodor's active ordinary-player rule set and the current bridge contract, missing FUMBLES_LOST evidence is the material ordinary-player coordinate causing this league-wide partial-player condition. Do not solve this by silently assigning zero fumbles lost.

This is a Forecast evidence/model gap that should be corrected generically if governed FUMBLES_LOST projection evidence can be produced. It is distinct from rare-event omissions such as 60+ FG increments.

### 2. K/DST independently blocks full Simulation authority
Hodor starts both K and D/ST and its active rules include K distance bands through 60+, FG misses, D/ST PA buckets, blocked kicks, defensive two-point returns and team special-teams events. Current family coverage therefore also emits `separate_k_dst_forecast_authority_required`.

This does not erase shared offensive Forecast anymore, but current Simulation admission requires `uncertainty_ready`, which is false whenever Forecast reports any Simulation authority blocker. Therefore no current 50,000-run Simulation is promoted.

### 3. Position strength, competitive classification and season outlook are downstream of Simulation
The live Simulation runtime is where optimized lineups, league-relative position strength, expected wins/playoff/championship distributions, Team Utility and calculated competitive state are assembled. When Simulation is not promoted, these fields remain unavailable by design. Their blank presentation is downstream consequence, not separate source failure.

### 4. FSFFL Intrinsic is a separate late-connect preseason-bootstrap gap
Broad Market Value is current-market evidence and can load independently. Canonical Shapley Intrinsic currently uses the preserved preseason Year-1 authority loader and requires `evidence_basis=preseason_baseline`. That loader is still scoped to the league-season artifact. A league connected after preseason therefore has no league-scoped preserved Year-1 baseline even when authentic league-agnostic pre-kickoff raw offense evidence exists elsewhere.

This is inconsistent with the already-approved late-connect architecture: authentic preserved league-agnostic PIT raw-stat evidence should be reusable/re-scored for a newly connected league without backdating current evidence. Forecast/Product should repair that bootstrap path for supported player families. Missing authentic K/DST preseason evidence remains unavailable rather than fabricated.

### 5. Draft-pick Broad Market blanks are a separate wiring issue
The current market runtime can produce pick cardinal / pick-variant evidence separately from player MarketPriceEstimate rows, while the Franchise pick presentation attaches `value_profile` only from the player-style `estimates` mapping. Therefore visible pick rows can show Broad Market unavailable even when pick evidence exists elsewhere. This is Presentation/Value wiring, not evidence that all pick market data is absent.

### 6. Green 7/7 is a readiness-semantics bug
PR #245 truthfully permits a background intelligence job to complete in a stable partial-authority state. However the top shell still maps that completed lifecycle to green `7/7 Core intelligence current`. Lifecycle completion must remain distinct from capability readiness.

Required corrective scope should therefore target these separate causes rather than treating all blanks as one failure.


### Non-regression guardrails for the post-PR245 corrective
The post-PR245 corrective must be backward-compatible with previously accepted behavior except where Management explicitly authorizes a truthfulness correction.

Required protections:
- existing fully supported leagues must retain their current State/Forecast/Simulation/Value capability unless a newly corrected governed Forecast input legitimately changes a model output;
- existing league-scoped preserved preseason baselines remain authoritative and must not be replaced by the late-connect bootstrap path; late-connect reuse is fallback/bootstrap only when the league-season artifact does not already exist;
- shared canonical raw Forecast evidence remains one authority; no league-specific duplicate projection database or Hodor special case may be introduced;
- adding governed FUMBLES_LOST evidence may legitimately change fantasy-point projections for leagues that score fumbles lost, but the change must be traceable to that newly supported coordinate and must not alter leagues whose scoring does not consume it;
- full K/DST authority gates, source-rights gates, uncertainty gates, and exact-state binding remain unchanged;
- accepted Market discovery, Decision-screen, zero-broad-changed-state-Simulation, Value authority separation, and existing lifecycle last-good restoration semantics must not change;
- the readiness correction may change labels/status presentation where the prior UI overstated capability; this is an intentional truthfulness correction, not permission to regress actual available intelligence;
- regression validation must include Hodor, arbitrary/synthetic Sleeper leagues with different scoring, and at least one existing fully supported league with previously complete intelligence. Existing full-capability outputs should remain within expected deterministic/model-version deltas and any intentional numerical change must be explained by the corrected Forecast coordinate.


## Physical iPhone acceptance — existing FSFFL league regressed after league switch
**State: ACCEPTANCE FAILED — EXISTING FULLY SUPPORTED LEAGUE / SWITCH-RESTORATION NON-REGRESSION**

Management physically switched from Hodor back to the existing fully supported FSFFL Dynasty league (`sleeper:1312071960615731200`, managed team `jimmygoodjob`) on iPhone/Safari.

Observed UI:
- shell reports green `7/7 Core intelligence current`;
- Home simultaneously shows `Position pressure point unavailable`;
- Current Simulation is unavailable;
- expected wins / playoff / championship are blank;
- franchise classification is `Not Classified`;
- position-strength rows are blank.

Durable database evidence:
- prior accepted fully supported State `203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed` still has non-invalidated `current_forecast_evidence`, `live_simulation_analytics`, and `current_market_value` artifacts;
- current selected FSFFL runtime context moved to State `8cd7b3cb80c924304e8a1bc33eecce020236efd175b33ef138ac66e97fe0c5ab`;
- the old complete intelligence bundle was therefore not deleted or corrupted;
- the new State is not byte-identical to the old State: league/teams/draft-pick ownership remain equal, while time-sensitive fields such as matchups, player/player-state, team-state, NFL byes, provenance and as-of changed.

Acceptance interpretation:
1. This is not evidence loss. The accepted complete FSFFL bundle still exists.
2. Because the newly selected canonical State materially differs, exact-state binding correctly prevents blindly attaching the old Simulation/Value bundle as current truth.
3. The product still fails the switching/lifecycle contract because a switch to an existing league may not present `7/7 Core intelligence current` while serving a new exact State with no current Simulation/position-strength/classification.
4. League switch must immediately distinguish:
   - usable canonical current State;
   - compatible reusable Forecast evidence;
   - last-good but stale exact-state intelligence;
   - current enrichment status / exact blocker.
5. If the current State requires recomputation, the shell must show that work truthfully and preserve safe last-good context only as explicitly stale/non-current evidence. It must not present lifecycle completion from the previous state/league as current 7/7.
6. Regression acceptance now requires switching Hodor → FSFFL → Hodor (and arbitrary valid Sleeper identities) without cross-state/cross-league readiness leakage, while preserving exact-state authority.

Do not use this incident to weaken exact-state binding or silently reuse stale Simulation. Repair switch/restoration/readiness orchestration and continue the already-authorized post-PR245 corrective through tests, merge, Render deployment, production Hodor validation, and production existing-FSFFL switch/regression validation before physical Market acceptance resumes.


### League-switch recomputation requirement
Management clarifies that last-good/exact-state restoration is an optimization and resilience mechanism, not a prerequisite for correctness.

When a user selects or reconnects any valid Sleeper league:
1. load and expose the current canonical LeagueState immediately;
2. attempt to reuse only intelligence artifacts that are provably compatible with that exact State / Forecast coordinate under existing authority rules;
3. if no compatible current bundle exists, automatically start or resume the normal governed enrichment pipeline for that newly selected State;
4. surface persistent progress/status while enrichment runs;
5. promote Forecast / Simulation / Value / derived analytics atomically when each authority gate clears;
6. if a stage cannot clear, expose the exact capability blocker while preserving usable State and any independently valid upstream evidence.

A previously complete league must therefore be able to reproduce its intelligence from canonical State + governed Forecast/Value inputs even if its prior complete bundle cannot be reattached. The product may not depend on finding a historical last-good artifact in order to become useful again.

Acceptance must prove both paths:
- **reuse path:** compatible persisted intelligence is restored without recomputation;
- **rebuild path:** when compatible intelligence is absent or stale, the app automatically recomputes the current State to the same governed capability level that the league's rules/evidence permit.

Do not weaken exact-state binding, source authority, or uncertainty gates to achieve this. The rebuild must use the same canonical Data → State → Forecast → Value → Simulation/Team Utility authority chain as a fresh valid league load.

For the current FSFFL regression, Management expects that the new State either:
- reuses compatible Forecast components and recomputes only invalidated downstream layers where allowed; or
- performs a full governed enrichment for the new State if compatibility cannot be proven.

In neither case may the shell claim green/full readiness before the current-State capabilities actually exist.


### Refresh Intelligence = league sync + intelligence reconciliation
Management defines the user-facing **Refresh Intelligence** action as the canonical manual league-sync/update operation, not merely a model rerun against the currently loaded State.

Required order of operations:
1. fetch/revalidate the currently selected Sleeper league from the provider;
2. persist/select the resulting canonical current LeagueState;
3. compare the new State to the prior State and determine which persisted intelligence remains provably compatible;
4. reuse compatible artifacts only under existing exact-state/input-fingerprint authority rules;
5. automatically rebuild every invalidated or missing governed layer for the new State;
6. expose persistent progress and exact capability/blocker status until reconciliation terminates;
7. atomically promote newly valid Forecast / Simulation / Value / derived analytics for the current State.

The current implementation path is not sufficient for this contract because `POST /api/intelligence/jobs` presently invokes the Forecast loader on the already-loaded `initial_state` before it refreshes canonical Sleeper State. A manual sync must not compute new intelligence from an old State and then attach/reconcile it onto a newly fetched State unless compatibility is explicitly proven.

Acceptance:
- a no-change sync should cheaply retain/reuse current governed intelligence;
- a changed-State sync should invalidate only affected layers and recompute them;
- a material roster/rules/matchup/player-state change must never leave stale downstream intelligence labeled current;
- if current evidence cannot rebuild a layer, the exact blocker must be surfaced while current canonical State remains usable;
- repeated manual Refresh Intelligence calls must be idempotent for an unchanged provider State;
- league switching and manual refresh must use the same underlying State-first reconciliation contract rather than separate semantics.

Product semantics:
**Refresh Intelligence = Sync league + refresh/reconcile intelligence.**
The existing button label may remain for now, but user-facing status should make the sync/rebuild lifecycle clear. A future wording change such as `Sync & Refresh` may be considered separately if physical testing shows the action remains ambiguous.

Do not weaken exact-state binding, Forecast authority, Value authority, Simulation gates, or last-good safety to satisfy this behavior.


## State-first corrective terminal handoff — 2026-09-26
**State: MANAGEMENT GATE — FUMBLES_LOST FORECAST AUTHORITY**

PR #246 and PR #249 complete the State-first league-sync, reuse-or-rebuild, and truthful capability-readiness contract. PR #251 makes preserved-preseason fallback replay retain truthful partial coverage; PR #252 invalidates stale pre-corrective Forecast artifacts so current State rebuilds under the new contract.

Production acceptance on current FSFFL State proves:
- canonical State current;
- current Broad Market/Value FULL;
- 1,675 raw Forecast observations;
- 335 partial player Forecasts;
- Forecast `partial_provisional`;
- Simulation unavailable;
- unique omitted active ordinary-player rule: `FUMBLES_LOST`.

The remaining failure is not league switching/rebuild/readiness orchestration. Under current authority, FUMBLES_LOST is core/material and the two-source preserved baseline contains no such coordinate. Implementation may not fabricate zero, borrow a different horizon, reuse stale full artifacts, or apply the auxiliary-single-source exception.

Durable handoff: `artifacts/implementation/state_first_fumbles_authority_20260926/IMPLEMENTATION_HANDOFF.md`.

Implementation waits for qualifying evidence or an explicit Management authority-policy decision. Market full physical acceptance remains paused because the current FSFFL state cannot promote Simulation.


## Management authorization — prepare 2026 ordinary-offense ROS lane
**State: AUTHORIZED PENDING QUALIFYING SOURCE EVIDENCE**

Management authorizes the product/Forecast architecture for a 2026 current-ROS ordinary-offense lane. Implementation may prepare provider-neutral horizon/artifact contracts, replay/fingerprint safety, current-forward consumer routing, provenance/coverage diagnostics, and tests that do not fabricate provider evidence.

Do not promote production ROS authority until Research supplies a qualifying same-horizon multi-source evidence package. Do not splice a ROS FUMBLES_LOST coordinate into the preserved preseason baseline.

When qualifying evidence arrives, implementation should:
- materialize one canonical current-ROS raw-stat Forecast ensemble for ordinary offensive players;
- preserve the authentic preseason baseline as a separate PIT artifact;
- score the ROS raw Forecast under each connected league's rules;
- rebuild current Forecast/Simulation/derived intelligence for the exact State;
- prove existing-league full capability and arbitrary-league non-regression;
- continue through CI, merge, Render and production validation before Management physical testing resumes.


## Management correction — implement only bounded FUMBLES_LOST supplementation
**State: AUTHORIZED PENDING QUALIFYING FUMBLES_LOST EVIDENCE**

The whole ordinary-offense ROS rebase is superseded.

Implementation should preserve the existing preseason/full-season ordinary-offense Forecast and add only a provider-neutral **current FUMBLES_LOST supplemental evidence contract** once Research supplies qualifying evidence.

The implementation must:
- keep the immutable preseason artifact unchanged;
- retain exact source acquisition/effective time and ROS/current horizon;
- normalize the supplemental coordinate to the scorer/Simulation's target period or rate explicitly;
- tag current scored Forecast lineage as supplemental/mixed-vintage where consumed;
- exclude the supplement from preseason/PIT historical comparisons;
- require two-source material-coordinate authority and target-compatible uncertainty;
- avoid changing leagues that do not score FUMBLES_LOST;
- rebuild only affected current Forecast/Simulation/derived artifacts;
- prove no unrelated ordinary-player raw-stat projection changes.

No current provider is promoted by this authorization.


## First-party FUMBLES_LOST integration directive — 2026-09-26
**State: ACTIVE — FIRST-PARTY MODEL INTEGRATION / PRODUCTION ACCEPTANCE**

Research is complete and merged through PR #256. The accepted first-party model is:
`next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`.

Authoritative Research handoff:
- `artifacts/research/fumbles_lost_first_party_model_20260926/PRODUCTION_READINESS_HANDOFF.md`
- `artifacts/research/fumbles_lost_first_party_model_20260926/MODEL_SPEC.md`
- `artifacts/research/fumbles_lost_first_party_model_20260926/CURRENT_INPUT_ASSESSMENT.md`

Implementation must now complete the recovery path through production acceptance:
1. wire the frozen first-party model into the already-merged PR #253/#255 current-supplement seam;
2. use exact lost-fumble semantics and the accepted Week-2/current-state opportunity inputs only;
3. reproduce the frozen 2026 calibration scalar and non-zero uncertainty contract exactly;
4. preserve every unrelated offense Forecast coordinate and the immutable preseason/PIT baseline;
5. fail closed for missing/ambiguous identity or required current evidence; never substitute zero;
6. rebuild current FSFFL Forecast/Simulation/derived intelligence for the exact current State;
7. prove leagues not scoring `fum_lost` are regression-identical and Hodor/partial-authority behavior does not regress;
8. run focused tests + full CI, merge the implementation PR, deploy Render, and validate production FSFFL reaches legitimate full current player-scoring authority and Simulation before returning control;
9. persist exact production evidence and stop only at a permitted `OPERATING_PROTOCOL.md` terminal state.

Do not reopen provider-permission Research, broad scoring coverage, K/DST authority, Market redesign, or long-horizon Intrinsic work in this corrective.


## Post-PR #257 production-acceptance checkpoint — 2026-09-26
**State: ACTIVE — POST-MERGE CI CORRECTIVE + PRODUCTION REBUILD VALIDATION**

PR #257 (`f07252b1dd19307c3b3c8f769cabfee7de7d6fac`) is merged and live on Render as deploy `dep-darki1g473hc73bb7aeg`.

Pre-merge acceptance:
- PR CI: green;
- PR164 focused corrective regression: green;
- Live Forecast corrective trace: green;
- Corrective live provider numerical trace: green.

Post-merge main CI is **red**: run `36217723025` finished with **1 failed / 1660 passed**. The failure is `tests/test_product_webapp.py::test_cross_league_switch_never_serves_old_league_intelligence`, where the switched response reported `simulation_ready=True` instead of the expected fail-closed `False`.

Do not classify the directive complete or ask Management to test while this remains unresolved. Determine whether the assertion exposed actual cross-league readiness leakage or a race/test-contract issue caused by same-request completion of valid new-league intelligence. Preserve the underlying no-stale-cross-league contract either way, correct the implementation/test as required, and return main CI to green.

The live deployment currently restores the existing FSFFL league/state with `forecast=True simulation=False value=True complete=False` at startup. This is not yet production acceptance of the new supplement. After CI is green, perform the required current-State FSFFL rebuild and prove the first-party FUMBLES_LOST supplement is consumed, current player scoring becomes legitimately complete where required, and Simulation promotes. Persist exact production evidence before returning control.


## Post-PR #259 production acceptance regression — 2026-09-26
**State: ACTIVE — TWO-PLAYER FUMBLES_LOST COVERAGE GAP / SIMULATION REGRESSED**

PR #258 merged at `af8b854d79e689f484af4c5eab16c3abca1f0da9`. PR #259 merged at `85cb4254a418f21f2c788fc0d515d80bd8c102f3`; main CI is green and Render deploy `dep-darl4dt9fdbs73a28log` is live.

Production evidence is mixed and therefore acceptance remains open:
- at 2026-09-26T05:06:48Z, State `04f38468159c55d587a0aef6fc9eb4be997f3287dc02f3d03e703f09630ff505` reached legitimate FULL capability: 670 authoritative scored forecasts, zero partials, first-party FUMBLES_LOST supplement for 335 players, Forecast FULL, Simulation FULL, Value FULL;
- after a later fresh State sync at 2026-09-26T11:41Z, State `1a92ea28d0f66be7608442f1a1a3b3ea20da667409ef8fbbff894057050f214a` rebuilt from `live_full_season` evidence with 660 authoritative scored forecasts and **2 partial WR forecasts**. Simulation was correctly withheld with `partial_player_scoring_coordinates_present`;
- the two partial subjects are `sleeper:player:11630` and `sleeper:player:6149`; both omit only `fum_lost`. The first-party supplement contained 330 players and did not cover those two subjects.

This proves the architecture can restore full capability, but current production remains non-accepted because a fresh valid State can still introduce active offensive subjects outside the first-party supplement's mapped/current population.

Next corrective: explain and close the two-player supplement coverage gap generically without fabricating zero or special-casing player IDs; preserve degraded/fail-closed semantics where evidence truly cannot be established. Then rerun current-State FSFFL acceptance and cross-league/non-consumer regression. Stop only after production remains FULL on the current State or at a genuine permitted blocker/gate.


## Management clarification — localize the two-player coverage gap
**State: ACTIVE — GENERIC SUBJECT-UNIVERSE RECONCILIATION / PRODUCTION ACCEPTANCE**

Management rejects treating one missing coordinate for two players as a system-wide failure. Preserve fail-closed semantics, but localize incomplete authority to the smallest affected subject/consumer scope.

For the current FSFFL State, first-party FUMBLES_LOST generation must reconcile against the current canonical forecastable offensive subject universe and apply the accepted model tiers generically. Do not limit supplement generation to only subjects already present in a provider Forecast batch. Reuse the frozen model's deterministic identity recovery, history-only/current-only/cold-start/identity-light logic and non-zero uncertainty exactly; never substitute zero.

Current acceptance focus:
1. explain why `sleeper:player:11630` and `sleeper:player:6149` were omitted from the 330-player supplement while present in canonical State;
2. fix the generic population/reconciliation rule, not those IDs;
3. prove current canonical offensive subjects that satisfy the accepted model contract receive FUMBLES_LOST evidence even when provider-forecast membership changes;
4. distinguish truly unresolved subjects from merely provider-absent subjects;
5. make consumer readiness subject-aware: unrelated State/Forecast/Value/surfaces remain available, and Simulation blocks only when an unresolved subject can materially affect simulated outcomes under the current consumer contract;
6. rerun current-State FSFFL, Hodor, arbitrary-league, switch/restart and non-`fum_lost` regressions;
7. merge/deploy and prove the current production State remains FULL Forecast + Simulation after a fresh sync/rebuild before returning control.

Do not add a new heuristic, player special case, silent zero, or broad authority downgrade.


## Management correction — Simulation gates on its actual subject dependency set
**State: ACTIVE — CONSUMER-SCOPED READINESS CORRECTIVE / PRODUCTION ACCEPTANCE**

Production inspection confirms the two current partial `fum_lost` subjects (`sleeper:player:11630`, `sleeper:player:6149`) are unrostered in the current FSFFL State. Current runtime nevertheless adds `partial_player_scoring_coordinates_present` whenever *any* partial fantasy-point forecast exists, making universal Forecast incompleteness a league-wide Simulation blocker.

Correct this generically:
1. derive the Simulation-relevant subject set from the exact current consumer dependency graph (at minimum every rostered player the Simulation/lineup engine can actually use; include other subjects only where the consumer explicitly models their entry);
2. compute material-coordinate Simulation blockers only for partial subjects inside that dependency set;
3. preserve partial Forecast rows and explicit omission reasons for unrostered/unrelated players;
4. keep universal player-surface readiness separate from roster-based Simulation readiness;
5. do not special-case the two current player IDs, do not zero missing `fum_lost`, and do not weaken authority for rostered players;
6. add regressions proving: unrostered partial player does not block roster Simulation; rostered materially partial player does block; non-`fum_lost` leagues remain identical; switching/restart does not leak readiness;
7. deploy and perform a fresh current-State FSFFL sync/rebuild. Acceptance requires Simulation FULL despite these two unrostered player-specific partials, with those partials still truthfully visible on player/free-agent surfaces.

After this consumer-scoped readiness correction, separately continue the generic first-party supplement population reconciliation so provider membership changes do not unnecessarily omit otherwise model-eligible subjects.


## PR #260 production acceptance checkpoint — 2026-09-26 09:12 ET
**State: ACTIVE — FSFFL FULL RESTORED / CROSS-LEAGUE DURABLE-CHECKPOINT FAILURE REMAINS**

PR #260 merged to main at `bc16ebea6126b4b182adf9b9c5e9b3542031e54d`; post-merge main CI is green. Render deploy `dep-darruh8u01pc73dlh3l0` is live on that exact merge.

Fresh production acceptance after deploy proves the original FSFFL restoration objective is now functioning on the current State: Forecast FULL, Simulation FULL, Value FULL, overall FULL; no material partial-player blockers; first-party FUMBLES_LOST v4 reconciled to a canonical subject universe of 827 players with zero omitted subjects in the accepted FSFFL snapshot.

The acceptance sequence then failed at the **Hodor switch durability checkpoint**, not at FSFFL Forecast/Simulation authority. Exact production error at ~09:11 ET: `FSFFL persistence checkpoint timed out user=state-first-acceptance-20260926`, followed by `StateFirstAcceptanceError: hodor_switch canonical State did not durably checkpoint`.

Next corrective is therefore narrow: diagnose/fix the Hodor switch persistence checkpoint timeout without regressing the now-restored FSFFL FULL state, then rerun the entire FSFFL → Hodor → FSFFL State-first acceptance sequence and restart preservation. Do not reopen FUMBLES_LOST model authority or subject-scoping work unless new evidence proves regression.


## PR #261 post-deploy acceptance failure — exact-State supplement binding
**State: ACTIVE — CROSS-LEAGUE EXACT-STATE PERSISTENCE CORRECTIVE**

PR #261 merged at `c57bc394986ce871ceca672efaacb54f1346eed0`; post-merge CI is green and Render deploy `dep-dart6rgu01pc73dq4500` is live.

Fresh production acceptance again proves the existing FSFFL league itself reaches FULL Forecast + Simulation + Value. The cross-league sequence still fails after that success. The previous generic checkpoint timeout has narrowed to an exact-state binding failure while switching: `FSFFL persistence checkpoint failed ... first-party FUMBLES_LOST supplement does not match persisted State`, followed by `Synced Sleeper State could not be durably checkpointed`.

Do not reopen completed FUMBLES_LOST model or subject-universe work. Diagnose why the supplement/state pair being checkpointed during the Hodor switch is not bound to the same canonical State generation, preserve no-stale-cross-league guarantees, and rerun FSFFL → Hodor → FSFFL + restart acceptance before asking Management for full physical testing.


## Physical acceptance regression — Intrinsic global coverage failure + mobile readiness strip
**State: ACTIVE — INTRINSIC SUBJECT-SCOPE CORRECTIVE + MOBILE READINESS COMPACTION**

Physical iPhone/Safari acceptance on the current FSFFL league shows core Forecast/Simulation/Value at FULL, but Player Intelligence / Market Intrinsic is unavailable with: `Authoritative future Forecast contract unavailable: player-specific future-I1 scoring cannot reproduce the frozen standard coordinate for required players: [...]`.

Production logs confirm the failure is globalized: the current universal/rostered scoring universe contains many subjects outside the frozen standard Future-I1 coordinate, and the future scoring bridge currently fails the whole H3 contract instead of restricting compatibility to its governed subject set.

Corrective requirements:
1. preserve the existing frozen H3/Future-I1 authority and exact governed cohort; do not broaden H3 authority merely because current State or FUMBLES_LOST supplementation now covers a larger universe;
2. derive Future-I1 scoring compatibility over the actual H3-owned subject set;
3. eligible governed H3 players must continue to receive Intrinsic even when unrelated current-State/free-agent players lack the frozen standard coordinate;
4. players genuinely outside H3 authority remain explicitly unavailable at the player level, without collapsing Intrinsic for other subjects;
5. prove persisted/current H3 values and ranks for the governed cohort are unchanged;
6. cover Player Intelligence, Player Board/Market value lenses, rostered and all-player universes, and league switching/restart regressions;
7. do not mix this corrective with the active Y4+ Research work.

Physical acceptance also shows the shared mobile readiness strip has become too dense. On narrow/mobile layouts:
- when core capability is FULL, collapse to a compact single-line state such as “✓ Intelligence current” plus a small Refresh action; hide redundant Forecast/Simulation/Value FULL chips;
- while building, show step/progress + one short active-phase message + Refreshing state, not a second row of full capability chips;
- show capability chips/details only when they communicate an exception (partial/unavailable) or via an expandable detail affordance;
- preserve the thin progress line and truthful 1/7→7/7 lifecycle; desktop may retain richer detail if it fits cleanly.

Treat the Intrinsic regression and mobile strip compaction as the next app-acceptance corrective after the currently open exact-State cross-league switch defect. Do not return full physical acceptance until all three are validated together.

## Management execution order — current app acceptance
**State: ACTIVE — COMPLETE SWITCH + H3 INTRINSIC + MOBILE READINESS ACCEPTANCE AS ONE PASS**

The current directive is the union of the open PR #261 cross-league exact-State defect and the subsequent physical-acceptance findings. Do not treat these as three independent stop points and do not return after fixing only one.

Execution order:
1. **Exact-State switch correctness first.** Resolve why a FUMBLES_LOST supplement/state pair can be checkpointed against different canonical State generations during the Hodor switch. Preserve switch-safe State-first persistence and no-stale-cross-league guarantees.
2. **Production H3 Intrinsic subject scope second.** Restrict frozen Future-I1/H3 compatibility to the subjects actually owned by the governed H3 contract. Preserve exact existing H3 values/ranks for that cohort. Subjects outside H3 authority remain individually unavailable; do not synthesize H3 evidence or let them collapse the whole Intrinsic surface.
3. **Mobile readiness compaction third.** FULL on mobile should render as one compact current-intelligence state plus Refresh; building should retain the truthful thin lifecycle/progress treatment plus one short active-phase message; detailed capability chips appear only for exceptions/details.
4. **Validate together.** Required deterministic coverage includes FSFFL, Hodor, arbitrary Sleeper identities, exact-State persistence, switch/restart, no cross-league leakage, H3 cohort/rank invariance, Player Intelligence + Market/Player Board Intrinsic consumption, roster/all-player scope, and mobile readiness states.
5. **Merge/deploy, then production acceptance.** Rerun the entire **FSFFL → Hodor → FSFFL → restart** sequence. Acceptance requires the existing FSFFL league to remain FULL Forecast + Simulation + Value; Hodor to expose only legitimately available authority for its exact State; governed H3 Intrinsic to load for eligible subjects without global collapse; and the mobile readiness strip to remain truthful and usable.

Do not reopen the completed first-party FUMBLES_LOST model, Market discovery semantics, Y4+ Intrinsic Research, K/DST policy, or broader scoring coverage unless new evidence proves the active corrective depends on one of them.

Do not ask Management for another broad physical-device acceptance pass before this combined sequence reaches a permitted `OPERATING_PROTOCOL.md` terminal state.

## PR #262 live branch checkpoint — CI not yet acceptable
**State: ACTIVE — PR #262 OPEN / DO NOT MERGE**

PR #262 (`implementation/combined-acceptance-20260926-r1`) now contains the intended combined corrective: exact-State FUMBLES_LOST binding, frozen-H3 subject scoping, and mobile readiness compaction. Current focused Intrinsic diagnostics and several surface validations are green, but the current head is not merge-ready.

Latest CI evidence on head `9df1761335619beaa816016c5beb8f4d907346d2`:
- full CI: **1668 passed / 13 failed**;
- most failures are stale static-release/cache-generation assertions expecting the old `20260925-state-first1` generation and must be reconciled without weakening coverage;
- one failure is substantive and must not be dismissed as a fixture update: `test_same_league_state_advance_never_reuses_fum_lost_supplement_from_prior_state` currently shows exact same-State restoration dropping Forecast evidence (`forecast_evidence=None`) where exact compatible evidence should be reused;
- Home focused validation also fails a static-generation consistency assertion; PR164 focused validation currently fails the same old-generation expectation class.

Required continuation:
1. fix the exact-compatible same-State reuse regression first and prove stale/prior-State supplement evidence is still rejected;
2. reconcile static-generation expectations consistently across all affected surfaces/tests rather than blanket-bumping unrelated semantics;
3. rerun full CI and all configured focused workflows to green;
4. only then merge/deploy and execute the already-required FSFFL → Hodor → FSFFL → restart production acceptance;
5. do not return at green CI alone; the workstream terminates only after the deployed production acceptance reaches a permitted `OPERATING_PROTOCOL.md` terminal state.

## PR #263 merged — restart persistence acceptance
**State: ACTIVE — POST-MERGE CI / DEPLOY / PRODUCTION ACCEPTANCE**

PR #262 merged after all configured pre-merge workflows reached green and delivered the combined exact-State switch, governed-H3 scope, and mobile-readiness corrective.

Its production restart acceptance exposed one narrower persistence defect: when an isolated acceptance user advanced the shared league-scoped latest snapshot, another user's still-valid exact persisted State could restore empty because restart required the shared latest snapshot hash to equal that user's state_hash.

PR #263 — `Persistence: preserve user exact runtime across shared league advances` — fixes only that user-scoped restoration rule. It permits restoration only when the durable user last-good `state_id` and artifact input fingerprint both exactly equal that user's persisted context `state_hash`; nonmatching evidence remains fail-closed. Forecast, FUMBLES_LOST, H3 Intrinsic, K/DST, Simulation, Value and Market authority are unchanged.

PR #263 merged to main at `4cd571529f7d97cc83083dc3b49c1fcb0eb61643`. Pre-merge CI, PR164 focused regression and live Forecast trace were green.

Continue without returning control through:
1. post-merge main CI;
2. Render deployment of the exact merge;
3. complete **FSFFL → Hodor → FSFFL → restart** production acceptance;
4. verify exact league/user/State identity, no cross-league leakage, FSFFL FULL Forecast + Simulation + Value, governed H3 Intrinsic availability, and compact truthful mobile readiness;
5. persist the exact acceptance evidence and finish only at a permitted `OPERATING_PROTOCOL.md` terminal state.

If this passes, core reliability no longer blocks Market physical acceptance; Management/Performance should proceed immediately to Market testing and latency work.

## Physical acceptance reopened — product surfaces + readiness truth
**State: ACTIVE — PHYSICAL PRODUCT ACCEPTANCE CORRECTIVE**

Management physical iPhone/Safari evidence after the prior post-PR263 closeout invalidates the terminal acceptance conclusion for the product as a whole.

Observed production failures on the selected FSFFL league:
- Player Intelligence / Franchise surfaces show **FSFFL Intrinsic unavailable** for governed players;
- Player Intelligence Career & Forecast renders only the current-season point with Y2/Y3 distribution details unavailable, despite the production H3/future contract being expected to serve governed subjects;
- League Atlas fails to render with **“Unable to load League presentation module”**;
- the shared strip simultaneously reports **“✓ Intelligence current”**, which overstates readiness while material product capabilities are unavailable.

The post-PR263 State-first persistence acceptance remains valid for the narrower State/Forecast/Simulation/Value/restart contract, but it is **not sufficient product acceptance**. Do not reopen already-proven State-first persistence unless evidence points there.

### Required corrective
1. Reproduce and fix the exact production Intrinsic/future-forecast failure using the actual hosted vNext loader and selected FSFFL State. The acceptance harness previously did not exercise the lazy hosted H3/Intrinsic endpoint; add a production-path regression that does.
2. Reproduce and fix the League Atlas presentation-module failure on the actual hosted route.
3. Validate Player Intelligence Overview + Career & Forecast, Franchise player cards, League Atlas, Player Board/Market Intrinsic consumption, and the canonical Intrinsic endpoint against the same accepted league/user/State.
4. Preserve existing H3/vNext authority and governed subject scope. Do not broaden authority or patch with current-market/owner data.
5. Add a **product-surface acceptance gate**: a terminal app-acceptance state requires successful actual endpoint/render-path exercise for the major surfaces whose data is claimed ready, not only underlying runtime artifacts.
6. Re-run physical iPhone/Safari validation after deployment.

### Shared Intelligence / loading strip contract
The current binary “Intelligence current” treatment is insufficient.

While a refresh/build is active, the strip should temporarily expand enough to communicate:
- current phase in plain language (for example: Refreshing league state → Building projections → Running season outlook → Building values → Building Intrinsic / attaching intelligence);
- completed/usable capability state without fabricated percent completion;
- whether last-good intelligence is being served while new work runs;
- the last-good **as-of timestamp** when applicable;
- a disabled “Refreshing…” control.

When the required supported intelligence is healthy, collapse back to the thin mobile strip. The compact completed state should include:
- a truthful scope label, e.g. **“✓ Intelligence current”** only when the product-required supported intelligence is actually available;
- **“As of Sep 26, 3:00 PM”** (localized presentation) or equivalent;
- Refresh Intelligence;
- optional tap/expand affordance for provenance/details.

If core Forecast/Simulation/Value are current but an important separate capability such as governed Intrinsic is unavailable, do **not** use the unqualified “Intelligence current” label. Show **“Intelligence partially available”** or **“Core intelligence current · Intrinsic unavailable”** with the relevant exception. A surface/presentation failure also prevents full product acceptance even if core data is current.

Timestamp semantics must be explicit and derived from governed evidence/served State, not browser clock guesswork. Prefer the latest compatible promoted intelligence timestamp and expose State/Forecast as-of detail through expansion.

Do not return control until tests, CI, deploy, hosted endpoint validation, and physical acceptance reach a permitted OPERATING_PROTOCOL.md terminal state.

### Charter corrective — remove model-specific P0 runtime ownership from vNext
The active product corrective now includes an architecture requirement, not only a subject-scope bug fix.

The current vNext production builder directly calls P0-specific materialization/identity machinery. This allowed the P0 future-contract path to receive a governed subject-scope fix while vNext silently bypassed it. That is incompatible with the charter requirement for modular, replaceable models and one authoritative home per concept.

Required:
1. identify exactly which P0-origin components are still empirically authoritative (for example identity/source mapping and/or state-probability layer);
2. separate those components from P0-specific production orchestration behind a model-neutral Forecast primitive/contract;
3. make vNext own its complete current production adapter and governed subject scope;
4. preserve frozen numerical equivalence where the reused primitive remains authoritative;
5. ensure downstream Intrinsic/Player Intelligence/Value depend only on the stable FutureForecastContract, not P0/vNext internals;
6. audit the active vNext path for any other direct dependency on superseded model-specific orchestration;
7. add architecture/regression tests proving a future model promotion can replace the Forecast provider without reintroducing P0-specific runtime assumptions.

Do not perform a broad rewrite. The objective is the smallest clean boundary that restores the charter while fixing the live failure.

### Immediate priority — restore a usable beta before broader architecture cleanup
Management considers the current multi-day inability to meaningfully test the private beta a beta-availability incident.

Execution priority inside the active corrective:
1. restore the affected hosted surfaces to a usable, truthful state as fast as possible;
2. use the **smallest charter-correct** vNext/Forecast boundary change needed to remove the live P0 orchestration coupling and repair governed H3 subject scope;
3. fix the League static-module load failure and readiness truth in the same deploy;
4. do not broaden this into a large Forecast rewrite before the beta is usable;
5. if the active branch cannot restore usability quickly, evaluate whether a known-good deploy or capability-level feature gate can safely restore unaffected product testing while the deeper corrective continues;
6. once the beta is usable again, complete the remaining architecture audit/regression hardening before closing the directive.

Acceptance must include actual authenticated hosted endpoint/render-path validation and physical iPhone/Safari evidence. A green unit suite without a usable product is not sufficient.

## PR #265 physical iPhone acceptance failure — Intrinsic Year-1 compatibility + mobile readiness layout
**State: ACTIVE — DEPLOYED PRODUCT CORRECTIVE NOT ACCEPTED**

Exact deployed corrective:
- merge `002924b21ed436cb97995eac534af629b87fba5f`
- Render deploy `dep-das32op7lnhs73fde380`
- post-merge CI green
- physical iPhone/Safari exercised after deploy

Physical evidence:
1. During refresh, the new lifecycle strip behaves directionally correctly: `4 / 7 Running season outlook… · Last-good available`, Refresh disabled, and partial capability state is shown.
2. After build completion, the shared readiness/status region catastrophically collapses on iPhone: status text and capability pills render in an extremely narrow vertical column inside a large empty card on both Home and League. This is a product-blocking responsive presentation regression.
3. The completed state remains `Intelligence partial`; Intrinsic is unavailable even though core Simulation/Value return.
4. Hosted logs prove the Intrinsic failure is server-side, not merely presentation:
   `intrinsic_status=unavailable intrinsic_build=completed coordinate=forecast-vnext-a2-burr-20260922 reason=Authoritative future Forecast contract unavailable: vNext mapped subjects lack compatible governed Year-1 evidence`.
5. Hosted logs simultaneously prove the League backend is serving successfully (`FSFFL League Atlas served ... standings=12 simulation=True`). Therefore the current League failure is presentation/layout, not the prior static-module/API-load failure.

Required corrective:
- reproduce and fix the exact vNext mapped-subject ↔ governed Year-1 compatibility failure using the deployed FSFFL State; preserve governed subject authority and do not synthesize missing evidence;
- determine whether subject intersection/identity reconciliation is wrong or whether legitimate Year-1 evidence is actually missing, and fail only affected subjects if authority permits rather than collapsing governed Intrinsic globally;
- add a deployed-path regression for the exact compatibility condition that failed after #265;
- fix the mobile completed/partial readiness layout so the compact strip never creates a narrow vertical text column or giant empty container at iPhone width;
- verify the same shared component on Home and League, plus Franchise/Market where reused;
- preserve the working in-progress lifecycle behavior observed at 4/7;
- reconcile any readiness overclaim: hosted capability labels must match the actual governed consumer scope and must not say Full if the relevant product consumer is degraded;
- deploy the corrective and repeat actual iPhone/Safari acceptance.

Do not reopen already-proven State-first switch/restart persistence or the charter-correct vNext/P0 boundary unless new evidence directly implicates them.
Do not return at unit/focused CI. Terminal acceptance requires the deployed FSFFL State to show healthy governed Intrinsic plus a physically usable mobile readiness layout.

## PR #266 live hosted acceptance failure — Intrinsic reduced/fallback availability
**State: ACTIVE — HOSTED ACCEPTANCE FAILED AFTER DEPLOY**

Exact corrective:
- PR #266 merged to `fa3c1a5fc559d7ab3cb11ae6a0675e419481de9d`;
- post-merge CI green;
- Render deploy `dep-das3lh0jo6nc73a2tif0` is live.

The corrective targeted the post-#265 vNext Year-1 compatibility failure and catastrophic mobile terminal-readiness layout.

Fresh hosted acceptance after deploy failed at 2026-09-26 21:40Z:
- startup product readiness was partial with Intrinsic unavailable before reconciliation;
- hosted product acceptance then failed because governed Intrinsic was not **fully** available;
- exact runtime reason: `Authoritative Intrinsic is available through a validated reduced/fallback evidence path; missing fact-family coverage is explicit and no provider absence is inferred as football state.`

Interpretation:
- this is progress from the #265 hard incompatibility failure; the runtime now has an authoritative reduced/fallback Intrinsic path rather than the prior mapped-subject/Year-1 incompatibility collapse;
- however, product acceptance is still open because the deployed build has not demonstrated the required governed Intrinsic completeness for the accepted FSFFL product scope;
- the mobile layout corrective is deployed but still requires physical iPhone/Safari confirmation.

Required continuation:
1. determine exactly which Intrinsic fact families/subjects remain reduced or missing and whether that partial state is expected governed authority or a remediable production gap;
2. do not weaken the acceptance gate merely to make the probe green;
3. if full governed Intrinsic is legitimately available from existing authoritative evidence, repair the remaining composition/reconciliation path;
4. if only partial Intrinsic is defensible for some subjects, localize that partiality to the affected subjects/surfaces and ensure product readiness truthfully represents it rather than collapsing the whole capability;
5. rerun hosted product acceptance on the same deployed FSFFL State;
6. physically validate the #266 mobile completed/partial readiness layout on iPhone/Safari before terminal acceptance.

Do not reopen completed State-first persistence or the vNext/P0 boundary absent direct evidence.

## Physical Player Intelligence failure — history materialization exhausts beta memory
**State: ACTIVE — BETA AVAILABILITY / MEMORY CORRECTIVE**

Physical iPhone/iPad Safari evidence at ~18:21 ET after PR #266:
- Player Intelligence modal returned **HTTP 503** on iPhone and **HTTP 502** on iPad.
- Other ordinary product APIs were healthy immediately beforehand.

Hosted evidence:
- Player Intelligence history for the selected player repeatedly returned `202 Accepted` while the background history build ran.
- Render memory rose from ~473 MB to **532.9 MB** against a **536.9 MB** service limit.
- At 22:22Z CPU dropped to zero, memory reset to ~96 MB, and Uvicorn/application startup ran again at 22:22:34Z.
- The 502/503 therefore coincides with a single-instance restart at the memory ceiling.
- After restart memory rose back to ~380 MB within ~90 seconds.

Code-path diagnosis:
- `PlayerHistoryBackgroundCoordinator` correctly coalesces requests for one State/player and uses one outer worker, so browser polling itself is not spawning duplicate player jobs.
- However `PlayerHistoryService.player_history()` requests every detailed historical season concurrently (up to six workers).
- Each `_season()` materializes a dictionary for the **entire provider player population**, persists it, stores it permanently in the in-process season cache, and `player_history()` also holds each full season again in `by_season` while only one player's rows are ultimately needed.
- This whole-season × multi-season in-memory materialization is incompatible with the current 512 MB private-beta instance.

Required corrective:
1. make one-player Player Intelligence history memory-bounded; do **not** materialize/retain full-population multi-season maps merely to return one player's history;
2. prefer persisted player-season / player-career retrieval or stream/project the requested player from season evidence before retaining it;
3. if the existing season artifact must remain, process seasons sequentially or with strictly bounded concurrency and release each full-season structure immediately after extracting the requested player;
4. do not retain full-season provider maps indefinitely in process; use durable persistence as the cache and keep only bounded/player-specific in-memory results;
5. persist/reuse the final player-history result so repeated PI opens do not rebuild career history;
6. preserve the existing `202 loading` UX and request coalescing, but a background task must never be able to OOM/restart the only web instance;
7. add memory/shape regression coverage proving one player request does not load all historical seasons/populations concurrently or retain them after completion;
8. validate on the current free-tier 512 MB Render instance before considering a paid-plan workaround.

This failure is independent of Intrinsic authority. The latest persisted Intrinsic contract contains 335/335 governed estimates; the PI 502/503 is a runtime memory failure in historical-stat materialization.

Continue through tests, merge, exact Render deploy, hosted memory validation, and physical iPhone/iPad Player Intelligence acceptance. Do not return at green CI alone.


## PR #267 Player Intelligence history-memory corrective — deployed / physical acceptance blocked
**State: BLOCKED — AUTHENTICATED HOSTED HISTORY LOAD + PHYSICAL IPHONE/IPAD ACCEPTANCE REQUIRED**

PR #267 (`Player Intelligence: bound historical materialization memory`) is merged at
`d737012079345768ef5cfd19debff97e0ede1bba`.

Accepted implementation head `e914dafe6a3e59ab41dfebebf3fb7177f6d1bcdd` passed:
- full CI: **1,704 passed**;
- PR164 focused corrective regression;
- Live Forecast corrective trace;
- Corrective live provider numerical trace;
- League Atlas North Star focused validation.

The corrective is intentionally limited to Player Intelligence history availability:
- Player History no longer fans all historical seasons out concurrently;
- the PI path no longer retains a permanent full-population season cache;
- Sleeper season history has a player-scoped retrieval path that reduces the provider payload to the requested player before transformed materialization;
- historical seasons are processed sequentially for one player;
- raw player-season rows persist independently;
- the final scored player-career history persists/reuses under provider/source-version + player + season-range + LeagueRules identity;
- weekly fallback remains sequential/player-scoped;
- the existing HTTP 202/loading lifecycle and duplicate-request coalescing are preserved.

Exact Render deploy `dep-das4k27avr4c73909lsg` is live on the exact product-code merge
`d737012079345768ef5cfd19debff97e0ede1bba` on the current 512 MB beta service.
Fresh instance id: `srv-dae6k7vqj5pc73af7bt0-v5qcn`.

Pre-fix failure baseline from PR #266:
- memory limit: 536,870,900 bytes;
- memory reached 509,108,220 bytes in Render's sampled series immediately before the restart boundary;
- Management's physical observation recorded ~532.9 MB peak and HTTP 502/503;
- CPU dropped to zero and the sole instance restarted.

Post-#267 fresh-start observation:
- ~51 MB at process start;
- ~259 MB at 22:43Z;
- ~303 MB at 22:43:30–22:44Z;
- ~337 MB at 22:45Z;
- ~360 MB at 22:45:30Z;
- ~384 MB at 22:46Z;
- no post-deploy restart observed in that interval.

**Do not treat fresh-start memory as the hosted PI-history acceptance.** No authenticated
post-deploy request to `/api/player-intelligence/{player_id}/history` has yet reached the new
instance. The execution environment does not possess the private-beta Basic Auth/session and
does not provide a physical iPhone/iPad browser. Therefore the remaining acceptance gate is
external and concrete:

1. open a real Player Intelligence history on physical iPhone and iPad;
2. observe the normal 202 → ready/200 flow with no 502/503;
3. repeat the same player open to prove persisted final-career reuse;
4. inspect Render memory for that exact request window and prove the same instance survives,
   memory stays safely below the 536,870,900-byte limit and materially below the prior failure
   curve, and the reused open does not recreate the career-build spike.

This incident is independent of Intrinsic authority and State-first persistence. Do not reopen
either without new direct evidence.

Durable checkpoint:
`artifacts/implementation/player_intelligence_history_memory_20260926/IMPLEMENTATION_HANDOFF.md`

**BLOCKED — FORECAST / PRODUCT IMPLEMENTATION — PHYSICAL / AUTHENTICATED HOSTED PLAYER INTELLIGENCE HISTORY ACCEPTANCE REQUIRED**

### Remove redundant large intelligence-status card
Management physical iPhone acceptance decision:

The large Home card beginning **“Current intelligence is partially available”** is removed from the product.

Rationale:
- the shared thin readiness strip already owns intelligence lifecycle/current/partial state;
- the large card duplicates the same information, consumes excessive mobile vertical space, and weakens the Home information hierarchy;
- transient build details belong in the expanded thin readiness component while work is active, not in a second persistent card.

Required behavior:
1. preserve the thin shared readiness strip at the top;
2. while refresh/build is active, allow that strip to expand with phase, last-good/as-of, and capability detail;
3. when complete/partial/failed, the strip alone communicates readiness truth;
4. remove the separate large intelligence-status card from Home rather than merely hiding its text;
5. do not leave blank spacing/container residue after removal;
6. verify iPhone/Safari Home layout physically after the change.

This is a presentation/product-hierarchy correction only. It must not change readiness semantics or model authority.

### Intrinsic compatibility reuse — do not invalidate on unrelated LeagueState changes
Management physical observation: a normal league-State advance caused the readiness lifecycle to remain at **6/7 Building FSFFL Intrinsic** for minutes, even though prior user refreshes reused Intrinsic in ~0.5-1.0s.

Measured evidence:
- prior compatible user refresh: Intrinsic ~0.507s;
- current exact-State rebuild entered `building_intrinsic` at 20:34:16 ET and remained active minutes later;
- recent cold hosted Intrinsic builds have taken roughly 154-180s.

Code-path diagnosis:
- `ShapleyIntrinsicBackgroundCoordinator._key()` includes the full `league_state.state_id`, so every canonical State advance creates a fresh background lifecycle record;
- the durable Shapley artifact scope uses `league_material_fingerprint(league_state)`, which is still intentionally broad and invalidates on roster ownership, team state, draft picks, matchup results, player status, etc.;
- the actual Intrinsic cache input fingerprint already separately includes preserved Year-1 Forecast evidence, source lineage, and the complete FutureForecastContract.

Required corrective:
1. define an **Intrinsic-specific compatibility/input fingerprint** from the actual governed inputs consumed by Intrinsic/Future Forecast rather than full `LeagueState.state_id` or generic broad league-material identity;
2. use that compatibility identity consistently for background coalescing and durable reuse;
3. changes unrelated to Intrinsic authority (e.g. matchup scores, draft-pick ownership, team labels/FAAB, roster ownership if not mathematically consumed) must not force a cold Intrinsic rebuild;
4. changes that truly affect Intrinsic (scoring/lineup rules, governed player identity/team mapping where consumed, preserved Year-1 evidence, FutureForecastContract/model coordinate, or other proven dependencies) must invalidate correctly;
5. prove by tests that an unrelated State advance reuses the same Intrinsic contract quickly while a true Intrinsic-input change invalidates it;
6. preserve exact point-in-time State provenance separately; compatibility reuse must not relabel an older State as the current State.
7. keep the current build running; apply this at the next implementation checkpoint rather than interrupting an in-flight refresh.

The objective is to restore the prior sub-second compatible Intrinsic behavior without weakening authority.

### Correct Intrinsic readiness semantics — legacy activation coverage is provenance, not availability
Management review confirms that the current `partial_provisional` label is semantically wrong for the deployed vNext Intrinsic path.

Code evidence:
- `private_beta_shapley_runtime._FACTS` comes from the frozen `current_i1_facts_2026` activation bundle;
- its coverage flags (`injury_practice`, `participation_snaps`, `roster_continuity`, `role_opportunity`) are copied into completed-source provenance;
- `_missing_fact_families()` currently converts false legacy coverage flags into `missing_required_fact_families`;
- `build_shapley_intrinsic_contract()` then marks the entire contract DEGRADED whenever any such flag is missing or any future path is not literally labeled `rich`;
- the current vNext production Intrinsic computation itself uses governed Year-1 Forecast + FutureForecastContract + LeagueRules; the old completed-source H1 bundle is diagnostic/provenance and does not enter the Intrinsic sum;
- the deployed contract currently has 335/335 governed estimates and complete Y1/Y2/Y3 coverage.

Required correction:
1. do not classify current Intrinsic availability as partial/degraded merely because legacy activation-bundle provenance lacks injury/practice, participation/snaps, or roster-continuity flags;
2. do not require an evidence-path string of `rich` when the governed vNext path is explicitly authorized and complete;
3. distinguish **availability/completeness** from **evidence/provenance richness**:
   - availability answers whether governed Intrinsic values are validly present for the required subject scope;
   - provenance may separately disclose that optional/legacy evidence families were not part of the frozen activation package;
4. keep those coverage facts visible in methods/provenance diagnostics if useful, but they must not make Home/Franchise/Player Intelligence say `Intrinsic unavailable` or `partial` when the production contract is complete and authorized;
5. preserve fail-closed behavior for genuinely required missing inputs such as Year-1 authority, FutureForecastContract coverage, scoring compatibility, missing governed subjects, or actual model/contract failure;
6. add tests separating optional provenance gaps from true production-input gaps;
7. update hosted readiness acceptance so a complete authorized 335-player vNext Intrinsic contract is considered available even if legacy optional coverage metadata is incomplete.

This is a semantics/governance correction, not permission to fabricate or infer missing injury/snaps/roster evidence.

### Immediate corrective — dependency-scoped Intrinsic recomputation
**Priority: NOW — beta availability critical path**

Physical evidence showed a cold Intrinsic build of ~226.7s followed by a compatible reuse of ~0.203s. The product must stop turning ordinary State advances into cold Shapley rebuilds.

Implement the Management recomputation policy from DECISION_LOG:
1. define one authoritative `intrinsic_input_fingerprint` from only the inputs actually consumed by production Intrinsic;
2. use that fingerprint consistently for:
   - background-job coalescing,
   - durable artifact lookup/reuse,
   - invalidation,
   - readiness compatibility;
3. do not key recomputation on full `LeagueState.state_id` or generic `league_material_fingerprint`;
4. preserve exact State provenance separately from compatibility identity;
5. on a true Intrinsic-input change, launch the cold build off the user-critical path, keep last-good visibly available as stale/as-of evidence where permitted, and atomically promote the new contract when complete;
6. prove with tests:
   - roster trade / matchup-score / pick-ownership / timestamp-only State changes do not rebuild Intrinsic;
   - scoring or lineup-rule change does rebuild;
   - Year-1 Forecast evidence change does rebuild;
   - FutureForecastContract/model/subject change does rebuild;
   - season rollover does rebuild;
   - switching away/back reuses a compatible persisted artifact;
7. preserve frozen 2,048-permutation Shapley semantics. Do not lower the model quality to hide the latency.

After this corrective, kernel-level cold-build optimization can move to Performance unless cold builds remain a practical beta blocker.

### Football-state event handling — invalidate through Forecast identity, not raw status
Implementation must preserve the authority chain when applying dependency-scoped Intrinsic reuse.

- Fantasy roster ownership changes alone do not invalidate player Intrinsic.
- NFL-context changes (injury/return, NFL trade, release/signing, promotion/demotion, suspension/retirement) must cause the Forecast layer to reevaluate when current governed evidence changes.
- Intrinsic compatibility must depend on the resulting authoritative Forecast input/contract identity. If Forecast is unchanged, reuse Intrinsic. If Forecast changes, background-recompute Intrinsic and promote atomically.
- Do not add direct heuristic injury/status penalties to Intrinsic.
- Until Research promotes a governed H3 current-state update layer, preserve the frozen H3 authority and truthfully expose its as-of/provenance limitations rather than pretending those events are modeled.

## PR #268 live acceptance failure — Intrinsic dependency fingerprint is still volatile
**State: ACTIVE — LIVE ACCEPTANCE FAILED AFTER DEPLOY**

PR #268 merged at `00017f765713f0aeb0b0913755345f74a49110a9` and Render deploy
`dep-das711d9fdbs73c4ohmg` reached LIVE.

The implementation correctly:
- removed full LeagueState/state_id and generic league-material identity from the production Intrinsic reuse key;
- separated legacy provenance richness from Intrinsic availability;
- removed the large redundant Home intelligence-status card;
- preserved 2,048 Shapley permutations and PR #267 PI history behavior.

However, live persistence evidence proves the new dependency fingerprint is **not stable**:
- 21:30 ET fingerprint `ba9f4103...`
- 21:33 ET fingerprint `b60189a4...`
- 21:36 ET fingerprint `60188402...`
- 21:39 ET fingerprint `446cec3f...`
- 21:41 ET fingerprint `02a0b016...`

All five persisted contracts were `ready`, 335-player contracts for the same FSFFL league/model, yet each used a different input fingerprint within ~11 minutes.

Root-cause code evidence:
`intrinsic_input_fingerprint()` still hashes volatile observation/runtime/provenance fields including:
- Year-1 observation `as_of`;
- full Year-1 `provenance.model_dump()`;
- `year_one_evidence.runtime_result.evaluation_as_of`;
- full `FutureForecastContract.model_dump()`, whose provenance can also contain runtime/evaluation metadata.

Those are provenance/as-of records, not necessarily mathematical Intrinsic inputs. Including them defeats compatibility reuse and can repeatedly trigger cold Shapley builds even when numerical/authoritative Forecast content is unchanged.

Hosted product acceptance failed at 21:37 ET because Intrinsic was still building. Render memory remained below the limit (~493 MB vs 536.9 MB) and the later process shutdown was orderly; do not classify this as an OOM incident.

Required corrective:
1. fingerprint **semantic/model inputs only**—the exact values actually consumed by Intrinsic/Shapley and stable authority/version identities;
2. exclude retrieval/evaluation timestamps and non-mathematical provenance metadata from compatibility identity while preserving them on the persisted artifact for PIT audit;
3. prove repeated identical governed Forecast content across fresh loads produces the **same fingerprint**;
4. prove a true numerical Forecast change, subject-set change, scoring/lineup change, season change, or model/version change produces a new fingerprint;
5. rerun hosted acceptance and demonstrate one persisted/reused contract rather than repeated ready artifacts;
6. only after live reuse is stable should Management physically validate near-instant refresh/switch behavior.

Do not lower permutations or weaken Forecast/Intrinsic authority.

## 2026-09-26 23:47 ET — BETA AVAILABILITY INCIDENT: last-good presentation lost during State refresh
**Priority: IMMEDIATE / AVAILABILITY RESTORATION**

Physical iPhone/Safari acceptance after PR #269 exposed a severe lifecycle/presentation regression.

Observed sequence:
- Render restarted at ~23:46 ET after the temporary acceptance-runner environment cleanup.
- Startup restored persisted core runtime for FSFFL with Forecast=True, Simulation=True, Value=True, complete=True.
- Startup product readiness still reported partial because Intrinsic was not yet reattached to the in-memory coordinator.
- Opening the app automatically issued `POST /api/connect/sleeper/background/refresh` at 23:46:58 ET and advanced the served State to `5dc6ba9f...`.
- While the new State was reconciling, the product stopped presenting the previously usable last-good derived intelligence.
- Physical symptoms included:
  - thin strip saying `Intelligence current` while Forecast/Simulation-derived fields were unavailable;
  - canonical roster banner saying `21 players` while the Starters roster rendered `No players in this roster view`;
  - Home/Franchise/League strength and Simulation fields blank/unavailable;
  - Intrinsic marked preparing despite a compatible persisted 335-player contract;
  - reload showed `Restoring your league and last-good intelligence...`.
- Manual Refresh Intelligence at 23:49:06 ET launched a full rebuild.
- The rebuild completed successfully at 23:54:54 ET, but phase timings were:
  - Forecast ~33.9s
  - Simulation ~390.6s
  - Current Value ~3.5s
  - Intrinsic ~8.6s
  - attach ~30.0s
- Memory remained below the ~537 MB limit; this was not an OOM.
- Simulation latency is real, but the primary availability failure is that last-good presentation disappeared while the target State rebuilt.

Required corrective:
1. **Separate target/building State from served last-good intelligence.** A State sync/rebuild must not evict a compatible previously complete presentation snapshot until the replacement layers are ready.
2. The thin readiness strip must distinguish `State current / intelligence rebuilding` from `Intelligence current`; it must never report `Intelligence current` while required capabilities are unavailable.
3. On restart, restore compatible persisted Intrinsic into readiness immediately; do not require a fresh in-memory build lifecycle merely to rediscover a valid persisted contract.
4. Canonical roster membership must render from State independently of Forecast/Simulation. Missing derived fields may show unavailable, but a 21-player roster must never become an empty Starters/Bench/All Players view solely because Forecast/Simulation is rebuilding.
5. Home, Franchise, League Atlas and other surfaces should continue to display last-good derived intelligence with explicit stale/as-of treatment while a newer exact State is rebuilding, unless compatibility is genuinely unsafe. Do not silently relabel last-good as current.
6. Auto background Sleeper sync may remain, but it must be non-disruptive and coalesced. Page reload/open during an active sync/intelligence job must not spawn a second disruptive refresh or replace the target State again.
7. If a new State has no material input changes for a derived layer, reuse via dependency-scoped compatibility rather than rebuilding solely because State ID/as-of advanced.
8. Preserve State-first provenance and fail-closed authority. The fix is a dual-state serving lifecycle, not lying about currentness.
9. After corrective: test cold server restart → app open → automatic stale-State sync → manual Refresh → page reload during active build → FSFFL↔Hodor↔FSFFL. At every point, canonical roster must stay visible and last-good intelligence must remain usable/truthfully labeled.
10. Do not require Management to physically test again until hosted evidence proves the above and the app has returned to a stable usable state.

Simulation's ~390s exact 50K cold latency remains a separate Performance target, but must no longer make the product unusable while rebuilding.

### Additional physical evidence — 00:01–00:04 ET
Additional iPhone/Safari evidence after the 23:54 intelligence rebuild completed:

- At ~00:01 ET the shared readiness strip displayed **Intelligence current**, while Franchise roster cards still displayed **Intrinsic preparing**. This is false-green readiness / reattachment inconsistency.
- The server had a persisted ready 335-player Intrinsic artifact and other server paths logged `intrinsic_status=ready intrinsic_build=completed`; therefore the product must reattach/reuse the persisted contract consistently across all surfaces after restart/reconciliation.
- Player Intelligence for `sleeper:player:4881` returned HTTP 202 from ~00:01:22 until 00:02:02, then HTTP 200. Full PI was served successfully by ~00:02:41 with Intrinsic ready and Forecast years [1,2,3].
- During that cold PI load, memory remained ~457–461 MB against the ~537 MB limit on the same Render instance; no restart/OOM occurred. PR #267's memory corrective therefore held in this physical pass.
- CPU saturated the 0.15 allocation during the PI cold load. PI cold latency remains a Performance concern, but it is not the prior memory-crash regression.
- Pick ownership detail is functionally present but exposes raw Sleeper pick identifiers (e.g. `sleeper:...:pick:2027:1:7`) as primary UI text. Treat as presentation debt after availability is restored; do not let it distract from the lifecycle incident.

Acceptance requirements now explicitly include:
1. no `Intelligence current` strip while any required capability is still preparing/unavailable;
2. persisted ready Intrinsic must render as ready consistently across Franchise, Home, Market, League and Player Intelligence after restart;
3. PI cold history may show truthful loading, but must complete without crash and subsequent reopen must reuse the persisted career-history artifact;
4. availability/lifecycle restoration remains higher priority than pick-detail presentation cleanup.


## PR #270 hosted beta-availability acceptance — 2026-09-27
**State: MANAGEMENT GATE — PHYSICAL IPHONE / SAFARI AVAILABILITY ACCEPTANCE**

PR #270, **Product: preserve last-good intelligence through State rebuilds**, merged at `2c63a9b05225759ba521da3e75fb65146b30fbbe` from accepted head `d6d6ccd2c41515a66a79b1ac4b009532ef109130`.

Deterministic acceptance on the final head is green:
- CI — 1,724 passed;
- PR164 focused corrective regression;
- Live Forecast corrective trace;
- Home North Star focused validation;
- Franchise North Star focused validation;
- League Atlas North Star focused validation;
- Private-beta Intrinsic live diagnostics.

Render deploy `dep-dasa5vg473hc73fd8uo0` is LIVE on the exact PR #270 merge.

Hosted production evidence after deploy:
- startup restored FSFFL league `sleeper:1312071960615731200` with Forecast=True, Simulation=True, Value=True, complete=True;
- startup product readiness was `full` with Intrinsic=`full`;
- the state-first acceptance runner completed with overall **PASS**;
- observed sequence:
  - `fsffl_initial` — FULL Forecast / Simulation / Current Value / Intrinsic;
  - `hodor_switch` — truthful PARTIAL state with PARTIAL_PROVISIONAL Forecast, Simulation unavailable, Value FULL, Intrinsic unavailable;
  - `fsffl_return` — FULL Forecast / Simulation / Current Value / Intrinsic;
  - two subsequent manual-refresh steps completed successfully;
- no application ERROR/CRITICAL logs were observed in the post-deploy validation window.

This satisfies the required nonphysical gate before another Management device pass. The availability incident is not yet promoted to DIRECTIVE COMPLETE because the required physical target layer remains unexercised after PR #270.

Physical acceptance should verify:
1. app open/reload never blanks canonical roster while derived intelligence reconciles;
2. readiness never says `Intelligence current` while a required capability is preparing/unavailable;
3. same-league last-good fields remain visible and explicitly stale/as-of if a new target State rebuilds;
4. persisted Intrinsic appears consistently across Home, Franchise, League, Market and Player Intelligence;
5. FSFFL ↔ Hodor ↔ FSFFL remains truthful on device with no cross-league masquerading;
6. manual Refresh Intelligence remains non-disruptive and does not create an empty/false-green interval.

Until this physical gate passes, Market and general Performance remain held behind beta availability.
