Warning: truncated output (original token count: 41705)
Total output lines: 1787

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

For the current FSFFL State, first-party FUMBLES_LOST generation must reconcile against the current canonical forecastable offensive subject universe and apply the accepted model tiers generically. Do no…21705 tokens truncated… it in this workstream:
- retain the ~429.5 MB value as diagnostic engineering headroom;
- record/report a soft-budget miss;
- do **not** fail hosted product acceptance solely for exceeding that target;
- continue to fail on a real process recycle, 5xx/429 availability failure, State/presentation loss, or actual hard-limit/safety breach;
- continue to record peak/current RSS so memory debt remains visible;
- do not weaken the Render hard-limit safety boundary.

Do not let another hosted run return FAILED solely because the soft engineering target was exceeded.


## 2026-09-27 22:23 ET — PR #279 merged; Render startup hang before hosted acceptance
PR #279 merged successfully as `916f87e0661475d9ae5c0458c788ba356e802262`. Render build `dep-dassq1rbc2fs73a74b10` completed the package build successfully, but deployment remains `update_in_progress`.

Observed new-instance evidence:
- new instance `srv-dae6k7vqj5pc73af7bt0-qvhhw` emitted only Render's command launch line for `uvicorn fsffl.product.persistent_webapp:app ...`;
- no subsequent Uvicorn "Started server process", application startup-complete, request, product startup, or State-first acceptance logs are present;
- no app error/critical logs are present either;
- Render has not marked the deploy live and hosted acceptance has not begun on #279;
- prior ~64s Market logs belong to the old #278 instance and must not be attributed to #279.

Immediate directive: stop Market feature work. Diagnose the narrow startup/import/initialization hang on the exact #279 merge SHA. Determine the last reached startup boundary before Uvicorn application startup, restore health readiness, then rerun the existing hosted acceptance on that exact deployed code. Do not expand scope or reopen Research.


## 2026-09-28 — PR #280 isolates remaining hosted failure to Hodor Forecast source health
PR #280 is live as merge `9db51f8190dd7a1a17d75987ddc685b7b459a8b2` and materially validates the runtime corrective on the primary FSFFL league.

Observed on the exact live build before the Hodor switch:
- cold PI history: ~0.507s with Forecast years [1,2,3];
- active-reconciliation PI history: ~2.905s with compatible Y2/Y3;
- Market workspace read: ~0.309s, followed by exact cache-hit ~0.000s;
- post-automatic-sync RSS: ~370.2 MB current / ~412.5 MB max observed, within the engineering target and below the hard Render limit;
- stale-last-good presentation continuity held during changed-State reconciliation and promoted back to current/full.

The acceptance failure occurred specifically at `hodor_switch`. Hodor required fresh live Forecast acquisition and failed the existing source-health contract because only Razzball was healthy:
- CBS: response not a full-season QB projection page;
- FFToday: HTTP 403;
- NFL Fantasy: response lacked projection content.

Do not reopen Market/runtime architecture because of this failure. The remaining issue is Forecast-source availability / Hodor continuity. Preserve the source-health authority contract; do not reduce the independent-source requirement merely to make acceptance pass.

Primary FSFFL physical beta testing may proceed as a bounded smoke test while Hodor/cross-league Forecast continuity remains open. Do not claim full runtime terminal acceptance until the league-switch path is resolved or explicitly reclassified by Management.


## 2026-09-28 — Management directive: finish Hodor Forecast replay correctly
The remaining `hodor_switch` failure is reclassified as a **Forecast replay / league-switch continuity defect until proven otherwise**. PR #280's primary-FSFFL improvements remain accepted evidence and must be preserved.

Implementation must now follow `docs/operations/directives/20260928_HODOR_FORECAST_REPLAY_CONTINUITY.md`:
- inspect persisted governed Hodor Forecast before live reacquisition;
- distinguish raw Forecast evidence compatibility from downstream State/scoring compatibility;
- emit the exact replay rejection component rather than only `fingerprint_changed`;
- allow downstream-only changes to rebuild downstream layers without invalidating reusable raw provider evidence;
- preserve Hodor's PR #244/#245 partial-authority behavior;
- never weaken the two-source/source-health gate for genuinely new Forecast authority;
- if raw Forecast is genuinely incompatible and providers are unavailable, preserve truthful last-good presentation wherever authority permits rather than blanking unrelated surfaces;
- run and pass the real hosted FSFFL → Hodor → FSFFL journey, including persistence/restart and provider-outage replay coverage, without regressing PR #280 latency/memory or cross-league isolation.

Do not return on an intermediate finding while authorized corrective actions remain. Long-Term Intrinsic stays paused until this hosted gate closes.


## 2026-09-28 — Post-merge P1: #281 is not deployable as-is
A Codex review posted immediately after merge found a P1 defect in `restore_exact_state_intelligence()`: when the last-good State ID equals the current State ID but exact-State Forecast restoration rejects the artifact solely because the downstream first-party FUMBLES_LOST supplement is stale, the function can return before `restore_state_bound_raw_forecast_evidence()` gets a chance to replay the valid raw provider ensemble.

This reproduces the undesired path: valid persisted raw Forecast exists → stale downstream supplement causes exact restore rejection → raw replay is skipped → live providers are reacquired → outage can fail Hodor unnecessarily.

Immediate action:
1. repair the same-State branch so raw Forecast evidence can replay/re-score when only downstream supplement/state-bound material is stale;
2. add a regression that proves same-State stale-supplement + provider outage succeeds without provider reacquisition;
3. keep genuinely raw-material changes fail-closed;
4. merge the narrow corrective;
5. deploy the corrected merge SHA, not bare #281;
6. run the full hosted FSFFL → Hodor → FSFFL acceptance journey before returning.

Do not broaden scope or weaken authority gates.


## 2026-09-28 — Post-merge P1 after PR #282: stale Simulation can survive Forecast replay
PR #282 merged as `d9ac502f29e0511e0738b379ed9b5018ea43945f` and closes the same-State stale-supplement early-return defect. A post-merge review found a second P1 in the newly reachable replay path: the rebuilt Forecast may be persisted while an older same-State Simulation artifact remains valid under current restore checks. If reconciliation is interrupted before Simulation rebuild, restart can restore a mismatched Forecast + Simulation bundle and treat it as terminal reuse.

Immediate action:
1. ensure raw Forecast replay invalidates dependent Simulation, or require persisted Simulation restore to prove exact Forecast identity/fingerprint compatibility;
2. add a deterministic same-State replay → interruption/restart regression proving stale Simulation cannot reattach;
3. preserve Value/Simulation authority and cross-league isolation;
4. merge the narrow correction;
5. deploy the corrected merge SHA, not bare #282;
6. run full hosted FSFFL → Hodor → FSFFL acceptance before returning.

Do not broaden scope or weaken authority gates.


## 2026-09-28 — PR #283 next action: close P2 and finish deployment
PR #283 is open/mergeable and fixes the post-#282 P1 Forecast↔Simulation restart mismatch. Before merge, address the review P2 by querying Simulation persistence with the exact expected Forecast dependency fingerprint instead of inspecting only the newest State-scoped row. Add/adjust focused coverage if needed, then merge immediately, deploy the exact merge SHA, and run the full hosted FSFFL → Hodor → FSFFL acceptance journey. Do not stop at green CI or merge while authorized deployment/acceptance work remains.


## 2026-09-28 — Live #283 acceptance failure: PI history overlap timeout
Exact merge SHA `047b3386e81bb843cc8b71408d05b0b81f38b792` is deployed and live. Hosted acceptance currently fails at:
`pi_history_during_active_reconciliation: PI history timed out`.

Immediate action:
1. reproduce the PI history request while active reconciliation is running on the live/corrected line;
2. identify whether the timeout is caused by foreground starvation/lock contention/heavy historical materialization or by an obsolete acceptance threshold;
3. if product-path real, restore low-single-digit/persist-first PI history behavior under overlapping reconciliation without changing Forecast/Simulation/Value/Intrinsic semantics;
4. if harness-only, correct the acceptance condition without weakening real availability checks;
5. rerun full hosted FSFFL → Hodor → FSFFL acceptance on the corrected SHA lineage;
6. do not broaden scope or reopen completed replay work absent evidence.


## 2026-09-28 — Superseding root-cause directive: atomic published intelligence generation
Physical testing on live #283 shows the runtime exposes half-built same-State reconciliation to readers. Current source makes the mechanism explicit: `set_forecast_evidence()` immediately replaces the live context and clears Simulation/Value; `set_simulation_analytics()` then keeps Value absent; stale presentation continuity only serves when the served State ID differs from current State. Consequently surface availability can flicker while the global status still appears current.

Stop treating `pi_history_during_active_reconciliation` as an isolated timeout. Implement `docs/operations/directives/20260928_ATOMIC_INTELLIGENCE_PUBLICATION.md`: separate working vs published intelligence generations, preserve the prior compatible published generation through same-State refresh, atomically promote the replacement only after coherent terminal checkpoint/presentation build, and bind readiness/banner semantics to the published generation. Add cross-surface generation-ID and interruption/failure regressions, then deploy and rerun full hosted acceptance. Do not broaden into model/research work.


## 2026-09-28 — Post-#284 Work red-team: one managed-team publication race remains
Independent read-only red-team of current main `e2b7676516dbb18ff5b5763a6d0508685c99c53b` found one concrete P2. During active reconciliation, `select_team` can change the published managed team while the working generation retains the earlier team. Finalization may persist model artifacts + published-generation manifest + user pointer before the runtime publication path rechecks the selected team and raises `managed team changed during reconciliation`. A restart can then restore publication/team state that does not match the user's latest selection.

Immediate action:
1. validate team/generation identity before writing the published manifest/pointer and protect it through durable commit + in-memory publication, or serialize/rebase publication with managed-team selection;
2. add a deterministic interleaving regression that changes team during the commit window and proves failed/cancelled publication cannot advance restart authority or lose the latest selection;
3. preserve all #284 atomic-publication and generation-ID behavior;
4. merge the narrow corrective, deploy exact merge SHA, then run full hosted FSFFL → Hodor → FSFFL plus same-State/read-overlap/managed-team acceptance;
5. do not broaden scope.


## 2026-09-28 — After #285/#286/#287: runtime fix is in; make the managed-team proof real
PR #285 merged the managed-team publication serialization/identity fix. PR #286 added hosted coverage, but post-merge review found the proof can miss the intended race because its surface probe may allow reconciliation to complete before `select_team`, and it validates copied `selected_team_id` instead of the actual returned Franchise `franchise_team_id`. Hosted follow-up then exposed a separate cold exact-State team/publication identity restore defect; PR #287 fixed that and current main is `2c0c6d0aefc0cc21913e6090b70f706c29e0b430`.

Immediate action:
1. repair the #286 acceptance interleaving so the alternate-team switch is guaranteed to occur while a working generation is still active (switch immediately after observing activity or revalidate before switching);
2. assert the actual Franchise/team-scoped returned identity, not only context metadata;
3. preserve #285 serialization and #287 cold-restore behavior;
4. deploy the exact corrected merge SHA and rerun full hosted FSFFL → Hodor → FSFFL plus same-State/cross-surface/managed-team acceptance;
5. do not broaden scope.


## 2026-09-28 — Final stabilization gates after #289 / open #288
PR #289 merged the intended managed-team acceptance correction. Do not consider stabilization terminal yet. Post-merge review found that selection can still occur while the worker is in checkpoint/presentation promotion outside the final store lock, deleting the active working generation and causing generic FAILED publication. Coordinate selection with the **entire final publication sequence** or classify this stale-work invalidation as an intentional interruption without advancing publication authority.

Open PR #288 also needs its two review P2s closed: carry a served publication generation only when the persisted publication's selected team matches the active team, and expose that served generation only when the same league/different-State/visible-snapshot predicate actually permits presentation continuity.

Then merge the corrected lineage, deploy the exact SHA, and run full hosted FSFFL -> Hodor -> FSFFL plus same-State/read-overlap/cross-surface/managed-team/restart acceptance. Return for physical iPhone/Safari validation only after that passes. Do not broaden scope.


## 2026-09-28 — PR #290 CI gate: served generation lost in active changed-State restore
Current #290 head `3ac755799e3f9d7a91e7ecf947e9d95f084ae908` has all focused checks green but full CI fails 1/1780 tests: `test_changed_state_restore_carries_only_team_matched_served_publication_generation`. Persistence restore carries the valid team-matched `served_publication_generation_id`, but `PersistentPrivateBetaRuntimeStore.restore_user()` produces an active `ServedIntelligenceSnapshot` with `publication_generation_id=None`. Repair that exact propagation path without weakening team-match / same-league / different-State / visible-snapshot guards. Full CI must turn green before merge. Then deploy exact merge SHA and complete hosted + physical acceptance. No scope expansion.


## 2026-09-28 — Post-#290 P1: cross-user publication/restore deadlock
PR #290 merged as `213c95014155de698b25681244024f4a0a66aa6b` with full CI green. Stabilization is still blocked by one post-merge P1 verified on current main: `PrivateBetaRuntimeStore` uses a store-global `_publication_lock`, while `PersistentPrivateBetaRuntimeStore` uses a store-global `_restore_lock`. A publication sequence can hold `_publication_lock` and wait on checkpoint/restore bookkeeping guarded by `_restore_lock`; concurrently another user's cold restore can hold `_restore_lock` and call `set_league_state()`, which waits for `_publication_lock`. This creates an unbounded lock-order inversion / deadlock.

Immediate action:
1. remove the cross-user lock inversion, preferably by keying publication serialization per user or otherwise establishing one consistent lock order;
2. preserve all atomic-publication, managed-team and served-generation semantics from #284-#290;
3. add a deterministic two-user regression: one user in final publication/checkpoint while another cold-restores; both must complete and preserve correct publication identity;
4. full CI green;
5. merge corrected SHA, deploy, run full hosted FSFFL -> Hodor -> FSFFL + same-State/cross-surface/managed-team/restart acceptance;
6. return for physical iPhone/Safari validation only after hosted success.

Do not broaden scope.


## 2026-09-28 — Stop serial stabilization patching; close the lifecycle class
Management no longer accepts the pattern “fix current P1 -> merge -> discover adjacent lifecycle defect.” Follow `docs/operations/directives/20260928_STABILIZATION_CLOSURE_PROTOCOL.md`.

Treat the current cross-user `_publication_lock` / `_restore_lock` inversion as one symptom inside the full publication/persistence/restore/identity concurrency class. Correct the ownership/ordering cleanly (per-user publication sequencing preferred unless a global invariant requires otherwise), then run the required deterministic single-user + two-user lifecycle matrix and bounded stress. Before merge, obtain a read-only red-team of the whole lifecycle and address every concrete P1/P2 it finds. Only after whole-class proof + full CI should the corrective merge/deploy and hosted acceptance occur. Do not broaden into model semantics.


## 2026-09-28 — PR #291 status: whole-class fix in progress, one checkpoint-coalescing CI failure
#291 head `7bcf6121688aa49f02cd4fbd4037925ca7d8503f` implements per-user lifecycle serialization, independent user checkpoint ordering, two-user concurrency coverage, restart/interruption cases and bounded stress. Pre-merge review surfaced shared-league snapshot ordering and idle-executor retention; current branch includes follow-up handling/coverage for both.

Full CI still fails 1/1795 at `test_same_state_checkpoint_queue_coalesces_to_latest_context`: durable runtime context writes contain only final `team:b`, while the historical test expects initial `None` then `team:b`. Determine the correct durability contract rather than changing the assertion mechanically. If latest-context-only coalescing is intended and restart-safe, update the test and document the invariant; if the initial State-only pointer is required for correctness, restore it without reintroducing blocking/global serialization. Then rerun the full closure matrix, full CI and pre-merge red-team before merge/deploy.


## 2026-09-28 — #291 merged; move to deployment + hosted acceptance
PR #291 merged as `dbe7fccaceca525e0586389dcc5388764fa015a3`. Whole-class pre-merge lifecycle audit is clean: full suite 1,796 passed, deterministic single/two-user concurrency matrix and bounded stress are green, and no remaining concrete P1/P2 lifecycle defect was found on corrected head `a5efeeedfae165c197724bd4f47170c3463c18b7`.

Do not reopen implementation unless hosted evidence reveals a concrete regression. Immediate action is deploy the exact merge SHA and run the required hosted FSFFL -> Hodor -> FSFFL plus same-State/changed-State/cross-surface/managed-team/restart/two-user lifecycle acceptance. Return for physical iPhone/Safari validation only after hosted success.


## 2026-09-28 — #291 hosted acceptance externally interrupted by Render free-tier idle sleep
Exact runtime merge SHA `dbe7fccaceca525e0586389dcc5388764fa015a3` was deployed as Render deploy `dep-datdlnugekts73adssi0` and became live at approximately 21:25:41Z. Startup restored the real beta user with full Forecast/Simulation/Value/Intrinsic authority and ~293 MB RSS.

Hosted acceptance materially progressed without a runtime failure:
- cold FSFFL reconciliation completed and atomically published one full generation across all checked surfaces;
- active-reconciliation PI history completed in ~0.49s;
- changed-State refresh kept readers on the prior coherent generation, then atomically promoted all checked surfaces to the replacement generation;
- Hodor completed truthfully with partial Forecast / full Value / Simulation unavailable under the existing K/DST authority blocker, and all checked Hodor surfaces shared one publication generation;
- peak observed acceptance RSS was ~445.5 MB, above the soft ~429.5 MB engineering target but below the ~536.9 MB hard Render limit.

At 21:40:41Z the exact #291 instance shut down gracefully, exactly 15 minutes after becoming live. There was no traceback, OOM, hard-memory breach, acceptance failure, or replacement deploy. Render metrics showed ~374 MB memory immediately before shutdown. The acceptance thread itself performs internal calls and generated no inbound HTTP traffic, so the free-tier idle-sleep policy interrupted the journey before the FSFFL return / managed-team / final same-State legs could finish.

This is an **operational hosted-acceptance blocker, not evidence of a #291 runtime regression**. Do not claim hosted PASS or request physical iPhone/Safari validation yet. The full acceptance must be rerun while the exact runtime lineage is kept awake by real inbound traffic (or an acceptance-only equivalent) for the duration; do not shorten or skip required lifecycle legs merely to fit the free-tier idle window. No Forecast/Simulation/Value/Intrinsic semantic work is authorized by this blocker.


## 2026-09-28 — ACTIVE: first-load regression recovery
The runtime lifecycle concurrency work from #291 remains valuable, but physical acceptance exposed a beta-availability regression in the basic first-load path.

Follow `docs/operations/directives/20260928_FIRST_LOAD_REGRESSION_RECOVERY.md`.

Key starting evidence:
- PR #54/`0021aefc...` and PR #56/`a8527e1...` are the known-good connect behavior reference: league usable in memory -> Connect completes; persistence asynchronous; Safari shows immediate progress.
- Current hosted connect still waits for `wait_for_checkpoint(..., timeout=30.0)`, preserved through PR #261/`c57bc39...`.
- Physical clean-reset test: connect accepted at ~22:45:29Z; product-context read ~51.6s; State persisted ~22:47:52Z; no explicit team choice, but browser-local team restoration issued select-team calls; fresh Forecast acquisition then failed/stopped without a coherent new publication or clear terminal user-facing failure.

Do not patch these as unrelated symptoms. Restore the complete first-load journey while preserving atomic publication, per-user lifecycle serialization, switch safety and final-generation durability. Required pre-merge proof: true clean first-run with empty server + browser state, restored session, league switch, restart, focused regressions, full CI, first-load/session/switch red-team. Deploy exact SHA and run controlled hosted clean-first-run before returning for physical iPhone/Safari.


## 2026-09-29 — #292 deployed; continue from Hodor acceptance failure
Exact merge SHA `8c162c5a7bf6120ecc72566e72dd11f634a93ee9` is live. The targeted primary-FSFFL path is behaving materially better in hosted acceptance: coherent initial publication, ~0.405s PI overlap, last-good continuity during rebuild, coherent changed-State promotion, and peak RSS ~386.9 MB.

Acceptance then failed at Hodor switch with `LiveForecastSourceHealthFailure`: only Razzball healthy; CBS invalid full-season response, FFToday 403, NFL Fantasy missing projection content.

Do not stop at this provider failure and do not weaken source-health rules. Determine why Hodor entered fresh acquisition rather than replaying compatible persisted raw Forecast evidence if such evidence exists. If replay should have been available, fix the narrow replay/restore handoff and rerun the remaining clean-first-run/restored-session/switch/restart acceptance. If fresh acquisition was legitimately required, return to Management with exact compatibility evidence showing why and what non-authority-breaking acceptance path remains. No model-semantic expansion.


## 2026-09-29 — Architecture audit adds mandatory cold-restore/Connect gate
The read-only runtime architecture audit confirms the analytical authority chain is sound but identifies a residual P1 availability exposure: foreground `get()` may synchronously run durable restore when no State is in memory, under the same per-user lifecycle coordination used by fresh Connect activation. This leaves persistence recovery capable of delaying fresh State activation.

New controlling corrective: `docs/operations/directives/20260929_RUNTIME_ARCHITECTURE_AUDIT_CORRECTIVE.md`.

Current lineage:
- #293 merged as `49ce8cae4f588fefc7c879e643504ee1b015cf42` and is live;
- current hosted acceptance is running; do not interrupt it absent a concrete failure;
- #293 review raised a replay P2: discovery must continue past newer incompatible raw artifacts to find older compatible governed evidence.

After the active hosted run completes, continue under the corrective directive. Required before stabilization close:
1. reconcile #293 hosted evidence;
2. resolve any still-open compatibility-scan P2;
3. make foreground `get()` an in-memory read rather than a synchronous durable-restore path for fresh Connect;
4. move restore to explicit orchestration outside fresh State activation and install only if captured identity remains current;
5. prove deterministic cold-restore vs fresh-Connect behavior, true clean first-run, restored session, FSFFL -> Hodor -> FSFFL replay/switch, and restart;
6. full CI + bounded P1/P2 red-team + exact-SHA hosted acceptance;
7. only then return for physical Safari validation.

Do not broaden into model semantics or foundation work.


## 2026-09-29 — Continue after #293 hosted partial success + idle cutoff
#293 exact merge SHA `49ce8cae4f588fefc7c879e643504ee1b015cf42` is live. Hosted acceptance now passes the prior Hodor hard stop: Hodor publishes coherent partial Forecast/full Value with Simulation correctly withheld for K/DST, then the journey returns to FSFFL with a coherent full generation. Repeat PI history is ~0.306s and peak RSS ~405 MB.

The instance then shut down gracefully at the 15-minute Render free-tier idle boundary before the remaining restart/final legs could complete. No terminal acceptance PASS was emitted.

Next action is not another Hodor redesign. Continue under `docs/operations/directives/20260929_RUNTIME_ARCHITECTURE_AUDIT_CORRECTIVE.md`:
1. verify/close the #293 replay-scan P2 (continue past newer incompatible raw artifacts to older compatible governed evidence);
2. remove/prove the cold durable-restore-before-fresh-Connect dependency so foreground `get()` does not synchronously gate fresh State activation;
3. add deterministic cold-restore vs fresh-Connect coverage;
4. rerun full CI + bounded P1/P2 red-team;
5. deploy exact corrected SHA;
6. rerun hosted acceptance with a permitted keep-awake/inbound-traffic mechanism so the free-tier idle policy cannot truncate the required clean-first-run/restored-session/FSFFL -> Hodor -> FSFFL/restart journey;
7. return for physical Safari only after terminal hosted PASS.

Do not broaden scope or weaken Forecast authority.


## 2026-09-29 — ACTIVE blocker after #294: managed-team durable checkpoint timeout
Exact #294 merge SHA `a0dcb92b3aa3fc08431076b404f03a9900bdaf0c` is live. Hosted acceptance passes the prior critical legs: FSFFL initial publication, rebuild continuity, Hodor, FSFFL return, fast PI, and two manual refreshes. The keep-awake mechanism also prevents Render's prior 15-minute idle cutoff.

The run fails before restart with:
`FSFFL persistence checkpoint timed out user=runtime-clean-first-load-pr292-20260928`
and
`StateFirstAcceptanceError: managed-team selection did not durably checkpoint`.

Continue from this exact failure. Do not rerun or redesign successful Hodor/Forecast work.

Required:
1. trace the managed-team selection checkpoint from in-memory team change through checkpoint queue/coalescing to durable runtime context;
2. determine whether this is real durability starvation, queue/coalescing ownership, wrong barrier/generation observation, or an acceptance-harness defect;
3. do not fix by merely increasing the timeout or putting persistence back on the foreground Connect/read path;
4. preserve #294's memory-only foreground `get()`, explicit restore, late-restore identity guard, replay compatibility scan, atomic publication, and per-user lifecycle safety;
5. add deterministic coverage proving team selection durably checkpoints under concurrent/recent heavy reconciliation/checkpoint activity;
6. prove restart restores that exact team identity;
7. focused regressions + full CI + bounded P1/P2 red-team;
8. exact-SHA deploy and resume hosted acceptance from clean-first-run through restart/restored-session;
9. only after terminal hosted PASS request physical Safari validation.

No model-semantic scope expansion.


## 2026-09-29 — #295 exact SHA live; acceptance in progress
PR #295 merged as `9fb755d4de0e81adaa0d34ea2fb04159b711c3ab` after full CI (1,816 passed) and bounded P1/P2 red-team closure. The managed-team durability path is now lightweight, exact, State-gated, generation-bound, and covered through restart/fallback scenarios.

Exact merge SHA is live on Render deploy `dep-dati6o5g1s2s739fv4pg`; hosted acceptance is running. Initial FSFFL publication is coherent and PI remains responsive. Peak RSS briefly reached ~517.0 MB, above the soft ~429.5 MB target but below the ~536.9 MB hard Render limit. Do not interrupt the acceptance run solely for this soft-budget breach; capture whether memory falls back and whether later legs remain below the hard limit.

Next required gate remains terminal hosted clean-first-run -> rebuild -> Hodor -> FSFFL return -> refreshes -> managed-team durability -> restart/restored-session. Only then request physical Safari validation.


## 2026-09-29 — #295 code not yet disproven; hosted acceptance truncated by unverified keep-awake
The #295 exact SHA `9fb755d4de0e81adaa0d34ea2fb04159b711c3ab` reached Hodor and returned to FSFFL coherently, then the Render instance shut down at the free-tier ~15-minute idle boundary before the managed-team/restart leg.

Important correction: the assumed keep-awake was not active/effective. Logs show only one inbound `GET /` at startup and no recurring inbound traffic. Do not alter runtime durability logic because of this interrupted acceptance.

Next action:
1. establish a permitted recurring inbound request that is actually accepted/counts as activity;
2. verify in logs that it repeats before relying on it;
3. rerun exact #295 hosted acceptance through managed-team durability, restart, and restored session;
4. capture memory throughout. This run briefly reached ~532.1 MB by Render metrics versus ~536.9 MB hard limit, though it later receded. If next complete run again approaches the hard ceiling, treat memory as an active stabilization blocker;
5. physical Safari only after terminal hosted PASS.

Do not reopen Forecast/Hodor or managed-team design absent new runtime evidence.


## 2026-09-29 — ACTIVE blocker after #295 full hosted rerun: same-State publication identity changes
The verified keep-awake rerun on exact #295 merge `9fb755d4de0e81adaa0d34ea2fb04159b711c3ab` stayed alive through the required window and passed the prior managed-team durability blocker. Alternate team:2 was durably selected and served correctly after reconciliation interruption.

The next same-State publication-isolation job then failed:
`ValueError: published league/team/generation identity changed during reconciliation`
surfaced as
`StateFirstAcceptanceError: acceptance job intelligence:c754e8204ba6459d875a19655b5e9224 ended failed`.

This happened after `same_state_during_active_reconciliation` showed team:2 and readiness=rebuilding, and before restart/restored-session.

Continue from this exact boundary:
1. trace the same-State reconciliation's captured league/team/publication-generation identity from start through final atomic promotion;
2. compare it with the settled post-team-switch runtime identity and any presentation/publication mutation that occurs while the job runs;
3. determine whether this is (a) a correct stale-job invalidation exposed by an acceptance sequencing defect, or (b) an incorrect runtime identity mutation/ownership problem;
4. do not relax the final atomic identity guard;
5. preserve #295 lightweight managed-team durability, #294 memory-only foreground get/explicit restore, replay compatibility, and per-user lifecycle sequencing;
6. add deterministic coverage for: team switch completes -> durability settles -> same-State reconciliation starts -> foreground surfaces remain coherent -> terminal promotion succeeds for the new team identity; and the converse stale-job case must fail closed;
7. prove restart restores the exact team only after that same-State terminal publication;
8. focused regressions + full CI + bounded P1/P2 red-team;
9. deploy exact corrected SHA and rerun hosted acceptance with verified keep-awake through restart/restored-session.

No Forecast/Hodor/model-semantic scope expansion. Physical Safari remains HOLD.


## 2026-09-29 — #296 runtime corrective complete; stop on Forecast authority gate
PR #296 merged as `7d88ea87e316958e0580dd90d457fbe490bd9a0b` after focused coverage, bounded P1/P2 red-team, and full CI (1,818 passed). The settled-team -> same-State publication identity bug is corrected without weakening the final atomic stale-job guard.

Exact #296 hosted acceptance failed before reaching that runtime leg because live canonical State is now beyond the frozen Week-2 first-party FUMBLES_LOST contract:
`first-party FUMBLES_LOST v1 requires canonical completed_through_week=2`.

This is outside the current runtime corrective directive. Do not broaden Implementation into Forecast model/authority changes without Management authorization. Preserve the #296 runtime correction and all prior Hodor/restore/team-publication work.

Current status: MANAGEMENT GATE — Forecast/current-season authority. Physical Safari remains HOLD until a governed Forecast path allows the complete hosted lifecycle to reach terminal PASS.


## 2026-09-29 — #301 complete; next blocker is hosted hard-memory peak
#301 final head `fdf8b4ccacd331178c5a6ef2cc2068400b0f0e6a` passed trace, all focused lanes, full CI and live diagnostics. It merged as `be5db0e35e787c97eb560bbc0e88f59669e7b6e6` and was deployed exactly as Render deploy `dep-dau1prbncjis73ae44p0`.

The original hosted harness P1 is closed and live-proven: the cold PI probe now extracts `entry.player_id` from each `RosterEntry`, selected canonical roster player `sleeper:player:11565`, and completed State-only history during active enrichment.

The same hosted run then passed clean first-run, explicit team selection, terminal full FSFFL publication, PI Y1-Y3/full Intrinsic upgrade, changed-State stale-while-rebuild continuity + atomic promotion, and truthful/coherent Hodor publication. It failed only when the resource sampler evaluated Hodor:
- process lifetime peak RSS: `559,685,632` bytes;
- configured Render hard limit: `536,870,900` bytes;
- current RSS at failure: `461,594,624` bytes;
- coarse Render metrics observed ~525.7 MB nearby, below the process-level instantaneous peak.

Terminal state under OPERATING_PROTOCOL: **BLOCKED — hosted hard-memory gate**. The remaining FSFFL return, same-State, managed-team race, restart and restored-session legs were not run after this failure. Do not attribute this to the #301 harness fix, reopen #298 FUMBLES_LOST authority, alter PI readiness semantics, or relax #294/#295/#296 lifecycle/atomic-publication boundaries. Physical Safari remains HOLD pending Management authorization for the resource blocker.


## 2026-09-29 — Hosted lifecycle acceptance PASS after #306; release to physical Safari
Final staged restore acceptance completed on exact #306 merge `c5e6e23596a0fd2489f82c309ffdc241a5e06e80`, Render deploy `dep-dau72mlg1s2s73bnbjqg`.

Result: **PASS**.

The restore-mode run proved the final remaining lifecycle gate:
- exact durable FSFFL State restored: `7dbcbf4e355094eda76eafd24bb36294100a34841f3a94f0126ba32ad1d533f6`;
- managed team restored exactly: `sleeper:1312071960615731200:team:1`;
- publication generation restored exactly and remained unchanged throughout staged rehydration: `88cf14c2269a66c64714c0999474434fbc3cf765edc57d9a4d577aec85bf5a12`;
- Forecast, Simulation and current Value restored immediately from durable authority;
- initial restored surfaces were coherent/current on that same generation while readiness was truthfully partial only because Intrinsic had not yet been rehydrated;
- governed PI history completed, staged Intrinsic restore completed, Intrinsic became full, and product readiness became full without changing publication generation;
- Home, Franchise, League, Market and both Market Value Lens surfaces all remained current/published on the same generation before and after Intrinsic rehydration;
- restore-mode peak RSS was `308,518,912` bytes against the unchanged hard limit `536,870,900`, leaving `228,351,988` bytes of hard-limit headroom;
- terminal log: `FSFFL RUNTIME AVAILABILITY ACCEPTANCE PASS`.

This completes the realistic free-Render hosted lifecycle gate for the accepted #303-#306 stabilization lineage. No runtime/model corrective is indicated by the final restore run.

**Release status: READY FOR PHYSICAL IPHONE/SAFARI VALIDATION.**

Next action is product-owner physical Safari smoke/testing. Do not reopen stabilization architecture absent contradictory evidence from that physical test.
## 2026-09-29 — #307 browser Connect corrective merged; physical retest next
PR #307 merged as `326a79ce8dfcd37d1e5f30d3dd0f11762e3de71a` after full CI and all triggered focused/live lanes passed.

The live physical trace proved that the browser reached the background Connect route and polling while canonical FSFFL State eventually activated. The remaining browser defect was the manual preflight/same-league rejection path: canonical State could already be active while Safari still needed the context re-applied to visible selectors. Manual Connect now always runs the idempotent background handoff and applies the resulting canonical context.

The live trace also showed the already-completed state-first acceptance harness auto-running during the physical attempt. Its Render startup flags are now disabled; a clean restart confirmed no automatic acceptance workload.

Static assets use coherent release token `20260929-physical-connect1` to force Safari freshness.

Next gate is only the physical iPhone/Safari Connect retest through visible league/team selection. No server-only substitute and no model/resource architecture reopening.


## 2026-09-30 — Physical refresh lifecycle corrective (active)

Directive: `docs/operations/directives/20260930_PHYSICAL_REFRESH_MEMORY_ROOT_CAUSE.md`.

The physical Safari request at 04:11:47Z overlapped in time with automatic
Sleeper background-refresh polling. Render RSS peaked at 522.4 MB / 536.9 MB;
CPU saturated and the process restarted. State survived but current-State
Forecast, Simulation and Value were missing. This evidence supersedes the
prior #307 instruction not to reopen runtime architecture.

Current implementation coalesces a manual intelligence tap into an active
same-user/same-league Hosted Connect refresh, runs persistent-app State loads
through HeavyWorkCoordinator, emits RSS/active-claim telemetry at every
reconciliation boundary, and resumes missing exact-State layers after a
server-restart interruption. It includes deterministic coverage for concurrent
product/status reads, repeated staged value-lens requests, one State-load owner,
terminal usable core capabilities and restart recovery.

Known evidence limit: the old deploy emitted only coarse RSS samples, so its
specific 173–178 MB growth cannot be assigned to individual Python objects or a
single builder. Boundary instrumentation is in place to profile the next live
fresh build. Value-lens requests were staged/lightweight; no incident evidence
shows foreground capability reads reconstructing expensive model layers. #306
was a warm durable restore and did not profile the cold refresh journey.

Exit gates: run full CI and fresh exact-head review, merge/deploy, capture a
realistic fresh-build's stage RSS plus foreground responsiveness on Render,
verify usable Forecast/Simulation/Value and downstream capabilities, then
repeat physical iPhone/Safari acceptance. Do not change model semantics or the
hard Render limit. Until the live fresh-build and physical retest pass, status
is **BLOCKED — runtime acceptance**.
