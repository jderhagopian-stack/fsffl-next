# FSFFL NEXT — Decision Log

## 2026-09-24 — Repo-backed operating workflow
Decision: use repository Markdown as the primary durable Management ↔ worker coordination mechanism. PDFs remain optional human-facing artifacts.

Reason: reduce context loss, giant handoffs, and repeated reconstruction while preserving explicit authority and acceptance gates.

## 2026-09-24 — Outcome ownership with bounded authority
Decision: workstreams own assigned outcomes through acceptance and should exhaust authorized actions in each turn. PRs, CI, deploys, and intermediate findings are evidence rather than automatic completion.

## 2026-09-24 — Performance boundary at Forecast authority
Decision: Performance must not weaken Forecast governance to make the new league reach 7/7. The K/DST/new-league Forecast blocker transfers to Research/Forecast authority.

## 2026-09-24 — K/DST modeling is not a UI patch
Decision: research K and D/ST as potentially distinct fantasy asset/forecast families. Do not simply force them through the existing offensive-player model.

## 2026-09-24 — Separate K/DST from new-league bootstrap
Decision: a newly connected league lacking a preserved preseason baseline is a general bootstrap problem and must be solved separately from K/DST modeling.

## 2026-09-24 — K and D/ST Forecast subject model
Decision: K is a distinct Forecast family but remains an individual-player subject. D/ST is a canonical NFL team-season unit and must not be modeled as an ordinary human player.

Reason: the evidence and scoring semantics differ materially from QB/RB/WR/TE, while D/ST identity is inherently a team unit.

## 2026-09-24 — Rule-level Forecast evidence completeness
Decision: production fantasy-point promotion must be complete for every active non-zero scoring rule relevant to the subject. Missing raw evidence cannot silently become zero.

Reason: the research identified that the current material-domain guard can omit an active `fum_lost` rule when `FUMBLES_LOST` evidence is absent.

## 2026-09-24 — D/ST scoring bands require distributions
Decision: points-allowed and yards-allowed bucket scoring cannot be reconstructed from a season total or average alone. Forecast must carry game-level/distributional evidence capable of integrating the configured buckets.

## 2026-09-24 — Preserve existing source authority
Decision: the two-independent-source Forecast rule is not weakened for K/DST. Source eligibility becomes rule/metric specific, and aggregate sources do not automatically count as independent votes.

## 2026-09-24 — K/DST uncertainty is separate
Decision: K and D/ST require distinct empirical season-error and weekly-volatility calibration. Offensive position coefficients are not fallback authority.

## 2026-09-24 — Late-connect preseason bootstrap
Decision: annual preseason authority remains a league-agnostic immutable raw-stat artifact. A late-connected league may use an existing season artifact or a provenance-preserving migration of authentic retained PIT raw evidence; current pages may not be refetched and backdated.

If qualifying preseason evidence does not exist, preseason comparison is explicitly unavailable. Separately authoritative current-forward Forecast may still operate.

## 2026-09-24 — Research completion does not equal production resolution
Decision: the K/DST + new-league Forecast research directive is complete, but the production blocker remains until Management authorizes and accepts governed implementation, empirical evidence promotion, downstream compatibility, and lifecycle validation.

Completion artifact: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`.

## 2026-09-24 — Bounded K/DST implementation authorized
Decision: Management accepts the completed K/DST + late-connect Research contract and authorizes the staged implementation sequence in the persisted handoff.

PR #215 may implement contracts, scoring completeness, deterministic fixtures, and non-promoting calibration/outcome harnesses, but must not promote live K/DST provider authority, K/DST uncertainty coefficients, a fabricated 2026 preseason baseline, or downstream K/DST economics before their separate evidence gates pass.

## 2026-09-24 — Synthetic fixture zero is not production evidence
Decision: deterministic tests may include an explicit zero fumble-loss observation when the fixture itself defines a complete synthetic stat line. Provider/runtime code may not convert an absent fumble-loss field into zero. Missing active production evidence remains fail-closed.

## 2026-09-24 — Market North Star not product-accepted
Decision: physical-iPhone acceptance does not close the current Market implementation. The four-surface shell is useful, but opportunity quality, readiness truth, and mobile information hierarchy remain below the product acceptance bar.

## 2026-09-24 — Trade Discovery architecture moves ahead of Market acceptance
Decision: move the Trade Discovery Architecture Review forward as a dependency of Market acceptance rather than treating it as later Trade Center work.

Reason: a small high-signal feed must establish strategic relevance, cheap economic coherence, bilateral plausibility, and diversity before deep Decision/Simulation. Raw package generation plus a “needs full evaluation” label is not sufficient to earn scarce For You attention.

## 2026-09-24 — Opportunity before package
Decision: the Market review will define an Opportunity as a governed strategic object distinct from a generated trade package. Package variants are candidate implementations of an opportunity and must be clustered/deduplicated before presentation.

## 2026-09-24 — Market mobile simplification
Decision: Market must be recomposed around SEE → UNDERSTAND → INTERACT → DRILL DEEPER, with progressive disclosure and distinct jobs for For You, Trade Finder, Player Board, and Free Agents. Market-vs-Intrinsic remains a discovery lens rather than mandatory repeated top-level chrome on every surface.


## 2026-09-24 — Market discovery unit is Opportunity, not package
Decision proposed for Management acceptance: discovery uses three governed layers — OpportunityHypothesis, MarketOpportunity, and CandidatePath. Raw one-/two-/three-asset packages are subordinate variants inside CandidatePath families and cannot independently consume For You cards.

Reason: the shipped package-row-first implementation mechanically produces repeated target neighborhoods and spends attention before strategic/economic/bilateral screening.

## 2026-09-24 — Pre-Simulation Decision screen before For You eligibility
Decision proposed for Management acceptance: at least one representative path behind every For You item must complete a bounded pre-Simulation Decision screen using existing governed economics, package concentration/economics, mandatory-cut cost, roster consequences, and negotiation feasibility. Broad discovery must launch zero exact changed-state Simulation runs.

The default private-beta compute budget proposed by the review is eight representative paths, allocated one per distinct Opportunity family before second representatives. This is a tunable compute policy, not analytical authority.

## 2026-09-24 — For You is a diversity-constrained attention frontier
Decision proposed for Management acceptance: For You renders only `worth_attention` MarketOpportunity objects, maximum four by default. Search applies deterministic categorical ordering followed by explicit diversity caps. Exact named-target duplication never relaxes. The feed is not filled with market-match-only or unevaluated rows to meet a quota.

## 2026-09-24 — Bilateral plausibility without acceptance odds
Decision proposed for Management acceptance: negotiation-feasibility shapes and pre-Simulation bilateral consequences supply the primary plausibility evidence. Owner Intelligence may attach context-controlled descriptive owner behavior as optional evidence/tie-breaker. Market does not generate an acceptance probability and Owner Intelligence does not alter universal Value.

## 2026-09-24 — Core lifecycle readiness is not surface readiness
Decision proposed for Management acceptance: global 7/7 is explicitly Core Intelligence readiness. Player Board, Free Agents, For You, and Trade Finder publish separate consumer readiness. Optional Shapley Intrinsic preparation may degrade or progressively enrich a Market surface but must not blank already-governed Broad Market/State evidence.

## 2026-09-24 — Market vs Intrinsic is a discovery lens
Decision proposed for Management acceptance: Broad Market vs FSFFL Intrinsic disagreement remains prominent in Player Board and Player Intelligence and may seed a discovery hypothesis, but the two lenses are not blended and are not repeated as mandatory organizing chrome across every Market surface.


## 2026-09-25 — Accept Market / Trade Discovery architecture
Decision: Management accepts the persisted Market / Trade Discovery architecture handoff and authorizes its bounded implementation sequence.

Accepted contract includes:
- OpportunityHypothesis → MarketOpportunity → CandidatePath separation;
- package variants subordinate to Candidate Paths;
- For You worth-attention gating before presentation;
- four-card private-beta feed with family/diversity controls;
- bounded eight-path pre-Simulation Decision screening as a tunable compute policy;
- zero broad changed-state Simulation calls;
- descriptive-only Owner Intelligence role;
- Core 7/7 readiness separated from per-surface Market readiness;
- approved North Star interaction grammar and progressive-disclosure presentation.

Implementation must preserve authority boundaries and deterministic fixtures. The eight-path budget is a product compute policy, not model authority, and may be tuned only with retained benchmark/acceptance evidence. Physical-iPhone acceptance remains required after implementation.


## 2026-09-25 — Market implementation-level acceptance
Decision: PR #220 satisfies the Management-authorized Market / Trade Discovery implementation contract and may proceed to merge/deploy for physical product acceptance.

Evidence:
- OpportunityHypothesis → MarketOpportunity → CandidatePath is implemented;
- Search admission is target-family-first before bounded candidate truncation;
- cheap Decision-owned economics precede package-family pruning;
- the heavier pre-Simulation bilateral screen is bounded to eight representative paths;
- For You contains only `worth_attention` Opportunities and does not backfill from raw Search rows;
- exact changed-state Simulation calls during broad discovery remain zero;
- Owner Intelligence is descriptive only and does not alter universal Value;
- Core 7/7 is separate from Market-surface readiness;
- Player Board preserves Broad Market while optional Intrinsic builds;
- static release generation is `20260925-market-discovery1`;
- full CI plus Home, Franchise, League Atlas, PR164 corrective regression, and live Forecast trace are green on the accepted code head.

Market North Star is not product-closed by this decision. Repeat physical-iPhone/Safari validation of the merged/deployed build is the next required gate.


## 2026-09-25 — Market current-beta acceptance failed
Decision: the accepted Market architecture remains frozen, but the authenticated post-PR-#232/#235 physical-iPhone pass failed product acceptance. A bounded corrective is authorized for competitive-lens discovery semantics, an explicit Find opportunities submission lifecycle, focused zero-result exhaustion evidence, separate Forecast versus FSFFL Intrinsic availability tracing, and remaining mobile safe-area correctness. The existing eight-path preliminary Decision budget and zero broad changed-state Simulation boundary remain protected.


## 2026-09-25 — Provisional 2026 K/DST degraded-authority mode
Decision: Management authorizes a bounded 2026-only provisional K/DST Forecast tier that scores only governed supported coordinates and explicitly omits unsupported coordinates. Presentation, readiness, and analytics may expose the provisional contract with its limitations attached. Full-authority downstream consumers may not silently treat it as complete Forecast truth. The full K/DST authority gates and the 2027+ fail-closed boundary remain unchanged.

PR #237 merged at `33b969b04180893f7e582c0ebd76c54bea81961d`. PR #238 exact-league-state persistence and API binding is accepted as safety hardening within the same authority envelope; it must reconcile with current main and retain green regression coverage before merge.


## 2026-09-25 — App-wide lifecycle and Hodor corrective
Decision: Hodor is a new-league completion plus app-wide lifecycle failure, not a regression from a previously complete Hodor state. Performance owns the cross-surface lifecycle contract: user action → immediate acknowledgement → safe usable current or valid last-good State → persistent background-work status → validated atomic promotion → explicit current or failed state. Valid roster State must remain visible while derived intelligence is incomplete, and old-league evidence must never masquerade as the newly selected league.

Performance must trace the exact persisted State through Forecast, including the PR #237 provisional K/DST path, then Value, Simulation, readiness, and promotion before attributing the observed 2/7 condition to any stage.


## 2026-09-25 — Partial Forecast coverage must remain usable
Decision: unsupported or inherently unforecastable scoring events must not collapse otherwise valid Forecast coverage. FSFFL NEXT must preserve and expose every forecastable governed coordinate and score the supported portion of a league's rules while explicitly identifying omitted, unsupported, or unforecastable scoring components.

A league-specific scoring rule does not create a separate underlying player-projection truth. Canonical player/stat Forecast remains league-agnostic; league scoring transforms those shared coordinates downstream.

For material missing coordinates whose absence would make the resulting fantasy-point total misleading, the affected subject/consumer may remain blocked. For bounded rare or special-event coordinates where no credible projection exists (for example a 60+ field-goal increment or certain rare special-teams events), the system may expose a partial/provisional scored Forecast that omits the unsupported contribution, provided the omission, coverage status, and downstream authority limits are machine-readable and visible. Missing evidence must never be silently treated as zero, but it also must not erase valid projections for coordinates that can be forecasted.

This rule applies beyond Hodor/K-DST and should be implemented through the canonical FULL/PARTIAL/UNSUPPORTED capability model rather than league-specific exceptions.


## 2026-09-25 — Study single-source authority for bounded auxiliary coordinates
Decision: authorize a bounded Research study of whether one governed source can support selected empirically low-materiality auxiliary Forecast coordinates. No production authority changes yet.

Research must classify coordinates by measured scoring/outcome materiality and source quality, not by rarity or convenience. It must evaluate at minimum FUMBLES_LOST, the 60+ FG incremental contribution, low-frequency K/special-teams events, and appropriate material controls; quantify player/rank/lineup/team/50,000-run Simulation sensitivity where feasible; compare omission vs one-source vs multi-source vs realized outcomes; and propose a league-agnostic quantitative authority contract for a later Management decision.

Existing two-source, rights, semantic, uncertainty, exact-state and no-silent-zero rules remain authoritative during the study.


## 2026-09-25 — Refresh Intelligence is the canonical league sync action
Decision: the user-facing Refresh Intelligence action is the canonical manual league sync/update command. It must refresh Sleeper State first, establish the exact new canonical State, reuse only provably compatible persisted intelligence, and automatically rebuild invalidated/missing downstream layers.

The current ordering that builds Forecast from the pre-refresh State and refreshes Sleeper afterward is not the target contract unless compatibility is explicitly proven. League switching and manual refresh should converge on the same State-first reconciliation lifecycle.


## 2026-09-25 — What-If includes historical counterfactual replay
Decision: What-If is a generalized counterfactual engine with both current-forward and historical modes. The current single-player unavailability scenario is only a thin initial implementation.

Historical What-If must be able to branch from an authentic point-in-time league State and substitute a different past decision. It must keep two outputs distinct: (1) a point-in-time probabilistic counterfactual using only information knowable at the historical cutoff, and (2) a realized-world hindsight replay that holds later exogenous NFL outcomes fixed where appropriate and shows what the alternate decision would actually have produced.

These lenses may never be blended. “Good decision with bad outcome” and “bad decision with good outcome” must remain representable. Historical transaction/draft/waiver/roster lineage, point-in-time evidence, Forecast/Value/Decision versions and uncertainty should support the counterfactual rather than being replaced by present-day values.


## 2026-09-25 — Persistent league intelligence is the product-development filter
Decision: competitive review does not trigger a product pivot or immediate workstream reprioritization. FSFFL NEXT remains a persistent governed intelligence model of a fantasy league rather than a collection of isolated calculators.

Roadmap work should normally strengthen at least one of three dimensions: (1) the persistent league model, (2) the usability/time-to-value of governed intelligence, or (3) the value/shareability/identity of the league itself.

Immediate sequencing remains: league lifecycle/readiness correctness first; governed intelligence completeness second; Market quality/responsiveness third; unified core-surface experience next. Record Book, generalized historical What-If, behavioral/needs-aware Mock Draft and other long-term surfaces remain part of the North Star but should not displace current reliability work.

Owner Intelligence, historical persistence and counterfactual State are shared capabilities to be reused across future surfaces, not one-off feature silos. Preserve point-in-time evidence now so future historical analysis/counterfactuals remain possible.

Commercial differentiation should be described as the integration of Forecast, separate Value dimensions, league/owner behavior, Decision/Search, Simulation, history and counterfactuals against one governed league model—not as uniqueness of any single feature.


## 2026-09-25 — Provider-agnostic source architecture and staged rights
Decision: FSFFL NEXT remains provider-agnostic by architecture. External providers are replaceable evidence suppliers behind canonical FSFFL contracts; no core Forecast/Value/Simulation/Decision behavior should depend on provider identity when a canonical coordinate contract is sufficient.

Source rights are evaluated separately for the actual deployment stage. Private-beta use requires that the provider's terms/license permit the specific beta acquisition/storage/derivation/display pattern, but it does **not** require that long-term commercial rights already be secured. Sources permitted for beta but not yet cleared commercially must be tagged `commercial_recheck_required` and re-audited/replaced/licensed before any commercial launch.

Do not conflate analytical Forecast authority, private-beta usage eligibility, and commercial usage eligibility. Canonical policy: `docs/operations/SOURCE_GOVERNANCE.md`.


## 2026-09-25 — Accept auxiliary single-source certification framework with zero certifications
Decision: Management accepts the Research-recommended generalized `AUXILIARY_SINGLE_SOURCE` certification framework **in principle**, with **zero initial provider/coordinate certifications**.

This does not promote any production source or coordinate. FUMBLES_LOST remains core/material and is not eligible for this exception under the current measured thresholds. Source-specific certification remains a separate evidence-bearing action subject to semantic fit, source health, stage-appropriate rights, historical quality/stability, uncertainty, and automatic demotion rules.

Immediate implication: the framework is accepted for future bounded auxiliary coordinates, but it does not clear the current FSFFL FUMBLES_LOST blocker.


## 2026-09-25 — Existing FSFFL full-capability acceptance remains required
Decision: Management rejects the acceptance-policy escape hatch for the existing FSFFL Dynasty league. A previously fully supported league may not be reclassified as acceptably partial merely because stricter Forecast semantics exposed a missing material coordinate.

The current objective is to restore legitimate full capability under the governed model by supplying/recovering qualifying FUMBLES_LOST evidence or, only if supported by new evidence and a separate explicit Management decision, changing the underlying authority policy. Do not solve this by silently zeroing, stale-artifact reuse, weakening exact-state binding, or declaring the partial state acceptable.

Until this is resolved, physical Market acceptance and broader product testing that depends on Simulation remain paused.


## 2026-09-25 — Authorize 2026 current-ROS ordinary-offense Forecast lane
Decision: Management authorizes a bounded **2026 current-rest-of-season ordinary-offense Forecast lane/rebase** for current-forward QB/RB/WR/TE intelligence.

This is a whole-horizon authority decision, not a FUMBLES_LOST-only exception. The current-forward Forecast may use a governed current-ROS ensemble when qualifying same-horizon evidence is available. Do not splice ROS FUMBLES_LOST into a preseason/season baseline.

Required boundaries:
- preserve the authentic pre-opener/preseason Forecast separately for historical comparison, point-in-time analysis and any consumer whose contract explicitly requires preseason authority;
- never relabel current ROS evidence as preseason or backdate it;
- retain provider-agnostic canonical raw-stat Forecast architecture and exact provenance/horizon metadata;
- require the normal material-coordinate multi-source, source-health, semantic, independence, uncertainty and stage-appropriate rights gates for the ROS ensemble;
- no silent zero, cross-horizon substitution, stale scored-artifact reuse or Hodor/FSFFL special case;
- current-forward consumers may migrate to the governed ROS lane only when their evidence contract accepts current ROS authority;
- 2027+ returns to the normal governed preseason capture plus in-season current-forecast process; this 2026 authorization exists to recover a late-start private-beta current-forward baseline and must not become a permanent shortcut.

Immediate objective: restore legitimate full current-forward FSFFL capability, including FUMBLES_LOST, from a complete governed same-horizon ordinary-offense ROS ensemble.


## 2026-09-25 — Supersede whole-offense ROS rebase with current-only FUMBLES_LOST supplement
Decision: Management supersedes the immediately prior authorization for a whole ordinary-offense current-ROS rebase. That scope was unnecessarily broad.

The governed recovery path is now a **current-only supplemental FUMBLES_LOST coordinate** for present/future intelligence.

The existing preserved preseason/full-season raw Forecast for all other ordinary offensive coordinates remains authoritative and unchanged. FUMBLES_LOST may be supplied from qualifying current evidence only if the system:
- preserves the source's actual acquisition time and declared ROS horizon;
- converts/normalizes the coordinate into the target period/rate required by the current scorer/Simulation without pretending the source itself was preseason/full-season evidence;
- uses at least two independent eligible sources because FUMBLES_LOST remains core/material;
- carries non-zero target-compatible uncertainty;
- labels the resulting current Forecast lineage as mixed-vintage/current-supplemented where appropriate;
- excludes the supplemental coordinate from preseason comparison, historical PIT replay, and any claim about what was knowable before the source acquisition date;
- never writes the supplemental coordinate into or backdates the immutable preseason artifact.

This is not a license to mix arbitrary horizons. It is a bounded coordinate-level current-intelligence bridge where target-period normalization is explicit and provenance remains machine-readable.

The objective is to restore current FSFFL Forecast/Simulation without changing unrelated player projections.


## 2026-09-25 — Intrinsic Value should expose a horizon term structure
Decision: the current three-year Intrinsic implementation is a validated bounded production coordinate, not the permanent definition of dynasty value horizon.

North Star Value should expose **horizon-specific FSFFL Intrinsic coordinates** rather than only one blended long-term number. The intended conceptual structure is:
- near-term / current-window Intrinsic;
- validated three-year Intrinsic;
- longer-horizon dynasty Intrinsic using increasingly state/survival/role/terminal-value evidence rather than fabricated precise stat lines.

The long-horizon layer should not require exact Y4/Y5 box-score projections if the evidence cannot support them. Forecast should instead model the quantities that remain governable farther out: career-state/survival probability, expected role/production tier conditional on state, age/position trajectory, replacement surplus, uncertainty, and discounted terminal value.

These horizon-specific coordinates remain parts of **FSFFL Intrinsic**, not new universal Value families. Broad Market, League Market, and Team Utility remain separate dimensions.

Decision/Search may use the shape of a player's Intrinsic horizon curve as governed evidence. Examples include identifying immediate-production assets versus durable dynasty assets, matching opportunities to an owner's competitive horizon, and comparing packages that shift value from present to future. Search may not turn the horizon curve into a hidden master score or fabricated acceptance probability.

Implementation is not authorized by this decision. A later bounded Research program must determine validated longer-horizon targets, historical calibration, discount/terminal treatment, uncertainty, and whether a 5-year-plus or terminal formulation is empirically preferable.


## 2026-09-25 — Horizon research must measure ranking and positional distribution effects
Decision: the future long-horizon Intrinsic research program must evaluate not only model accuracy, but how valuation structure changes as the horizon changes.

Required comparative outputs should include:
- player rank changes across near-term, three-year and long-horizon/terminal Intrinsic;
- position-specific value distributions at each horizon;
- positional share of top-N and top-percentile assets by horizon;
- crossover players whose relative value materially rises or falls as the horizon extends;
- age/experience effects within position;
- concentration, dispersion and tail behavior by position;
- uncertainty growth by horizon;
- whether the current blended Intrinsic ranking hides materially different temporal value profiles.

These are analytical diagnostics, not permission to tune the model to produce a desired positional mix. Position distributions must emerge from Forecast/Value evidence and league economics, not from manual balancing.

Decision/Search may later consume governed horizon-specific coordinates and rank changes as evidence, while preserving separate universal Intrinsic values and downstream Team Utility context.


## 2026-09-25 — Do not make vendor permission the FSFFL recovery dependency
Decision: Management rejects a recovery plan that requires the user to solicit bespoke permission from external projection vendors before FSFFL can regain ordinary current intelligence.

The JerryGM + LineupExperts path remains documented as a possible future external evidence path, but it is removed from the immediate critical path.

Research is authorized to pursue a **first-party FSFFL FUMBLES_LOST Forecast model** using already-governed historical football outcomes/evidence and current canonical opportunity inputs. This is a Forecast-owned predictive model, not a one-source provider shortcut.

Authority for a first-party model is earned through preregistered target/feature definitions, strict point-in-time chronology, out-of-time validation, calibration/error analysis, non-zero uncertainty, current-population coverage, versioned artifacts, and fail-closed runtime behavior. The external two-independent-provider rule remains applicable to provider-ensemble evidence; it is not automatically a requirement that a separately validated first-party FSFFL model have two external vendor votes.

The model must predict exact FUMBLES_LOST rather than silently map total fumbles to lost fumbles. It may use governed current Forecast opportunity coordinates and historical player/team/position evidence only when those inputs are available at the evaluation cutoff. Market, dynasty value, Owner Intelligence, and current/future outcomes may not leak into training.

No production promotion is authorized until Research demonstrates a validated model materially better than omission / simple transparent baselines and hands off a frozen implementation contract.


## 2026-09-26 — Authorize bounded long-horizon Intrinsic research now
Decision: Management authorizes the long-horizon Intrinsic program to begin as a bounded **Research-only** workstream in parallel with the still-open FSFFL production-restoration Implementation work.

This authorization does not change production Value, Forecast, Search, Decision, Market, Team Utility, or the current validated three-year Intrinsic coordinate. It does not authorize implementation.

Research should determine empirically whether dynasty value is best represented by discrete horizon coordinates (for example 1-year / 3-year / 5-year), by detailed Years 1–3 plus a longer-term career/terminal component, or by another evidence-supported structure. Farther horizons must become less falsely precise; exact Y4/Y5 box-score projections are not required unless historical validation supports them.

The study must use chronological point-in-time/out-of-time methods where feasible, explicit baselines against the current three-year Intrinsic architecture, governed uncertainty that expands with horizon, and no named-player tuning. Candidate long-horizon inputs may include career-state/survival probability, role persistence/transition, age/position curves, conditional production tiers, replacement surplus, and terminal value. Discounting and terminal treatment must be tested rather than chosen to manufacture a desired ranking.

Required analytical outputs include horizon-specific player values/ranks, player rank deltas and crossover points, position-level value distributions, top-N/top-percentile positional share, concentration/dispersion/tails, age/experience effects, and uncertainty growth by horizon. Resulting positional mixes must emerge from evidence; Research may not manually rebalance positions.

Research should also identify how separate governed horizon coordinates could later inform Trade/Market/Search and roster construction while preserving universal Intrinsic coordinates and keeping Team Utility downstream. Do not create a hidden master score or acceptance probability.

Return at a Management gate with the empirical comparison, recommended horizon architecture, validation limits, and an implementation-ready contract only if the evidence supports one. Production three-year Intrinsic remains authoritative until a later explicit implementation decision.


## 2026-09-26 — Partial player coverage must be localized, not system-wide
Decision: a missing Forecast coordinate for one or a small number of players must not make unrelated FSFFL capabilities unavailable. Partial authority is subject-scoped and consumer-scoped.

State, unaffected player Forecasts, Broad Market/Value, historical evidence, and unrelated product surfaces must remain usable. A downstream consumer may be withheld only when the incomplete subject can materially enter that consumer's calculation and no governed bounded treatment exists.

For current Simulation specifically:
- do not fabricate or silently zero a missing material coordinate;
- first attempt to produce the coordinate under the already-accepted first-party model's governed history-only/current-only/cold-start/identity-light paths and non-zero uncertainty;
- the model population must be reconciled against the current canonical forecastable offensive subject universe, not merely the subset present in one provider Forecast batch;
- if a truly unresolved subject is outside the Simulation-relevant population, it must not block league Simulation merely because it exists in State;
- if a truly unresolved subject can materially enter simulated lineups/outcomes, preserve fail-closed truth for the affected Simulation authority until Research/Implementation has an authorized bounded treatment. Do not solve this by pretending the coordinate is zero.

The current two-WR incident is presumed to be a population/reconciliation defect until disproven: both subjects have deterministic Sleeper identity and position and were already present in prior State snapshots. Implementation should repair the generic supplement-universe/reconciliation path before considering any new authority-policy exception.


## 2026-09-26 — Unrostered player incompleteness cannot block roster-based Simulation
Decision: current league Simulation authority must be evaluated against the subjects that actually participate in the Simulation dependency graph, not against every player in the universal Forecast universe.

Production inspection of the current FSFFL State confirms the two remaining partial FUMBLES_LOST subjects, `sleeper:player:11630` (Roman Wilson) and `sleeper:player:6149` (Darius Slayton), are **not rostered by any FSFFL team**. They therefore cannot by themselves block the current roster-based league Simulation unless that Simulation explicitly models them as possible transaction/waiver entrants.

Required semantics:
- keep those player Forecast rows explicitly partial; do not fabricate or silently zero FUMBLES_LOST;
- Player Board / Free Agent / Market consumers may expose the player-specific incompleteness where relevant;
- current league Simulation, lineup optimization, standings/race and other roster-based consumers gate only on their actual subject dependencies;
- bench/taxi/IR or other rostered players remain Simulation-relevant when the consumer can use them through lineup/injury/roster mechanics;
- unrostered players become blocking only for a consumer that explicitly models acquisition/waiver/free-agent entry and therefore includes them in its dependency set;
- readiness must report scoped capability truth rather than letting unrelated universal-player incompleteness collapse the core league product.

This is a dependency-graph correction, not an authority relaxation. Missing evidence remains visible and fail-closed for the affected subject/consumer.


## 2026-09-26 — Long-horizon model selection must be empirical
Management does not want FSFFL to assume that Y5 is the correct breakpoint or that one model family should own every post-H3 horizon. The next Research phase must compare models from Y4 onward and let chronological out-of-time evidence determine whether different horizons or positions need different model families.

Production H3 remains the governed Intrinsic authority. New models may be benchmarked against H3, but nothing replaces H3 unless a later study shows materially better performance on the existing Y1-Y3 problem and Management separately authorizes a change.

Research may compare the current two_part_state benchmark with survival/hazard, multi-state career or role-transition, conditional-production, and other defensible model families across Y4-Y8. Position-specific and horizon-specific routing is allowed only when it is supported by stable validation and sufficient sample size. Simpler models should win when added complexity does not produce durable improvement.

Longer-horizon Intrinsic coordinates are intended as additional decision lenses that can be viewed according to the user's decision horizon or franchise timeline. They do not need to replace H3, and Team Utility remains downstream.


## 2026-09-26 — Intrinsic eligibility is scoped; universal player expansion must not collapse H3
Production H3 Intrinsic remains governed by its frozen Future-Forecast / I1 authority and must not be implicitly expanded merely because the current canonical player universe or a supplemental current scoring coordinate covers more players.

An unsupported player outside the governed H3/Future-Forecast subject set may have Intrinsic unavailable for that player, but must not make otherwise eligible players or the entire Intrinsic surface unavailable. Future-I1 scoring compatibility checks must be evaluated against the subjects that the H3 contract actually owns, with explicit per-subject unsupported status outside that set.

Implementation must preserve exact H3 values/ranks for the existing governed cohort and may not synthesize new H3 authority, silently zero missing coordinates, or use the broader FUMBLES_LOST supplement universe as authority to extend Intrinsic.

## 2026-09-26 — Accept comparative Y4+ model-family result and define next long-horizon architecture
Decision: Management accepts the completed comparative Y4+ Research result as the current long-horizon research standard.

1. **Annual model family.** `two_part_state` is accepted as the Research-standard annual cardinal family for QB/RB/WR/TE at Y4-Y8. This is not a production promotion. It is accepted because the six-family chronological comparison found no challenger or routed architecture with a sufficiently robust multi-objective advantage, especially once upper-tail/squared-error behavior is considered.
2. **No model breakpoint.** Management explicitly rejects treating Y5, or any other Y4-Y8 boundary, as an empirically discovered model-family breakpoint. A single family across these years does not imply equal precision.
3. **User-facing cardinal horizons.** For the next product-design phase, the default discrete universal Intrinsic horizons are **H1, governed H3, and H5**. H5 is a useful decision lens because it creates meaningful rank separation from H3; it is not a different model regime. H4/H6/H7/H8 remain governed Research/diagnostic coordinates available for validation, scenario work, and drill-down, but they should not become separate default top-level product scores unless later product evidence justifies the additional complexity.
4. **Terminal/career representation.** Management authorizes a separate Research-only terminal/career-state track using survival/hazard and career-state/transition evidence. Its purpose is a coarse persistence/state representation, not another falsely precise annual fantasy-point coordinate and not a replacement for annual Forecasts.
5. **Uncertainty before promotion.** No H5/Y4+ cardinal coordinate may be promoted into production Intrinsic until Research/Design defines and validates a long-horizon uncertainty/presentation contract that communicates horizon decay and position-specific uncertainty without false precision.
6. **Production H3 remains unchanged.** No H1-Y3 replacement, hidden blended master score, market anchor, owner-preference adjustment, youth bonus, QB premium, or Team Utility leakage is authorized.
7. **Downstream use.** Future Decision/Search/Trade surfaces may consume separate governed horizon coordinates as distinct evidence lenses once promoted, but Team Utility remains downstream and may not rewrite universal Intrinsic.

This closes the comparative model-family Management gate while opening only the bounded terminal/career-state + uncertainty/presentation Research track. Production implementation of long-horizon Intrinsic remains unauthorized.

## 2026-09-26 — Reopen long-horizon predictor selection before terminal/career modeling
Management has identified an important limitation in the completed comparative Y4+ model-family study: it compared six model families over a narrow inherited predictor set rather than re-opening long-horizon feature selection.

The tested annual Y4-Y8 predictors were limited to:
`age, experience, prior_pct, log_prior_points, log_y1, y1_pct, y2_ratio, y3_ratio, y2_delta, y3_delta`.

Therefore the accepted conclusion is narrower than previously stated:
**given that frozen 10-feature information set, `two_part_state` is the most robust tested annual cardinal family.**
It does not establish that the current feature set is sufficient or optimal for Y4-Y8.

The frozen historical evidence package already contains additional static player metadata not used in the Y4+ comparison, including draft year/round/pick, height, weight, college, conference, and rookie season, plus a separate seasonal-stat evidence cache. Earlier trajectory research also tested hierarchical career-stage state, player-specific residual history, and innovation/volatility on near-term Y2/Y3 gates; failure on those near-term targets does not prove irrelevance for Y4-Y8 survival, role persistence, or conditional production.

Management therefore supersedes the immediate terminal/career-state next step with a **Research-only long-horizon predictor discovery and ablation phase**.

Required design:
1. inventory all defensible point-in-time candidate features available historically, including static pedigree/physical attributes, age-at-entry/development timing, position-specific usage/efficiency, durability/availability where governed, role/team continuity where historical PIT evidence exists, and previously rejected near-term trajectory/residual/volatility states;
2. explicitly distinguish features that predict **career survival/relevance** from features that predict **production conditional on survival**;
3. test incremental information beyond the governed Y1-Y3 Forecast trajectory, rather than rewarding a feature for merely re-encoding current production;
4. use nested chronological development/selection with untouched holdout evaluation; do not screen features on the final holdout or on current named players;
5. permit position × horizon interactions only when sample size and held-out stability support them;
6. compare feature groups through ablation/addition against the current 10-feature baseline and test at least one regularized flexible challenger capable of discovering interactions without black-box authority;
7. control for historical coverage/missingness and era effects; a feature cannot be promoted because it works only in a recent, selectively observed subset;
8. preserve the prohibition on Market/dynasty value, Owner Intelligence, Team Utility, future outcomes, or other downstream/economic leakage into universal Intrinsic Forecast;
9. re-run model-family selection only if richer features materially change the information set; do not assume `two_part_state` remains optimal once the feature space changes;
10. report negative findings as valuable evidence and preserve a simpler model when added predictors do not improve robust OOT performance.

The previously accepted H1/H3/H5 product simplification remains provisional design direction only. No H5/Y4+ production promotion, terminal/career implementation, or final long-horizon architecture decision is authorized until this predictor-discovery gate closes.

## 2026-09-26 — Comprehensive long-horizon architecture search
Management further broadens the long-horizon Research directive. The goal is no longer only feature discovery followed by reuse of an incumbent model-family comparison. The study must jointly determine the best supported **information set, target decomposition, model family, and routing architecture** by position and horizon.

Nothing is preselected for Y4-Y8:
- `two_part_state` is a benchmark, not incumbent authority for the expanded study;
- one universal model is not preferred over position-specific or horizon-specific models;
- position-specific and horizon-specific models are not preferred over a shared/hierarchical model;
- H5 is not a presumed statistical breakpoint;
- discrete annual models are not preferred over continuous-horizon, multi-task, survival/transition, or ensemble approaches;
- a terminal/career representation remains a candidate output only if it is empirically superior/useful.

The study must use **all defensible point-in-time evidence available or reconstructable under current governance**, including the previously identified metadata/stat/trajectory families and any additional football evidence discoverable in governed historical sources. It must explicitly inventory unavailable-but-plausibly-useful features as data gaps rather than silently treating them as irrelevant.

Candidate architecture classes should include, where sample size and chronology permit:
- transparent linear/regularized and nonlinear baselines;
- two-part survival × conditional-production models;
- discrete-time hazard / survival and accelerated-lifetime-style approaches where appropriate;
- multi-state career/role transition models;
- cohort and age/experience curve models;
- tree/boosting or other regularized flexible interaction learners with interpretability diagnostics;
- shared/hierarchical or multi-task structures that borrow strength across positions/horizons;
- position-specific and horizon-specific specialists;
- continuous-horizon models;
- calibrated ensembles/stacking when they improve held-out performance without masking authority.

Research must test both direct annual-point targets and decomposed targets such as:
1. probability of remaining NFL/fantasy relevant;
2. role/state conditional on relevance;
3. production conditional on state/survival;
4. uncertainty/tail outcomes.

Selection must be nested chronological and avoid winner's-curse overfitting across many position × horizon candidates. The final untouched holdout may confirm or reject a frozen architecture but may not be used to iterate candidate definitions. Require minimum sample sizes, stability across folds/eras, missingness sensitivity, calibration, tail accuracy, rank/order utility, and economic bridge usefulness. Penalize unnecessary route/model complexity.

If evidence supports different models for QB/RB/WR/TE, different models at Y4/Y5/Y6/Y7/Y8, or both, Research should recommend that architecture. If a pooled/shared model wins, recommend that instead. If no material gain survives holdout, preserve the simpler baseline.

Production H3 remains untouched. A challenger may expose evidence relevant to H1-Y3 only as a separate, independently validated Management question. No long-horizon production implementation is authorized until this comprehensive study closes.

## 2026-09-26 — Dedicated Simulation engine efficiency phase after core/Market latency gates
Management directs a dedicated **general Simulation engine efficiency** phase immediately after the current core reliability acceptance and immediate Market foreground-latency corrective are cleared.

This is distinct from prior work that improved perceived or repeated latency through:
- durable exact-Simulation reuse/persistence;
- exact concurrent-request coalescing/single-flight;
- progressive answer delivery;
- quick-counter/frontier staging;
- foreground-cooperative pacing;
- State-only foreground reads while background Simulation runs.

Those remain valuable and must be preserved. However, PR #127 explicitly left the fresh 50,000-run Simulation kernel unchanged for later optimization. That deferred kernel work is now a planned near-term Performance priority.

Sequence:
1. finish current PR #263/core restart-switch acceptance;
2. immediately close the currently measured Market cold/focused foreground-latency problem because broad Market discovery intentionally performs zero changed-state Simulation and Simulation optimization will not solve that blocker;
3. then begin the general Simulation engine efficiency phase before resuming lower-priority product breadth.

Simulation optimization must start with measurement, not assumptions:
- benchmark canonical fresh 50,000-run league Simulation;
- benchmark changed-State/Trade Simulation;
- benchmark repeat/reuse path separately;
- profile RNG generation, player outcome sampling, lineup selection/optimization, scoring aggregation, matchup/standings updates, playoff/championship resolution, serialization/persistence, and orchestration overhead;
- distinguish CPU kernel cost from persistence/database/network/UI time.

Tier A optimization authority — preferred and pre-authorized:
- hoist invariant work out of Monte Carlo loops;
- reuse exact Forecast/scoring/schedule/state structures;
- replace repeated Python object/dict work with compact arrays/indexes where behavior is unchanged;
- vectorize or batch mathematically identical operations where deterministic output identity can be preserved;
- preallocate/reuse buffers;
- remove duplicate scoring/lineup computations;
- reuse exact stochastic/player-draw inputs across exact-compatible downstream evaluations when doing so preserves the canonical random experiment;
- preserve exact caching, durable reuse, single-flight and restart-safe semantics;
- improve instrumentation and stage-level timing.

Tier B — requires a new Management gate before implementation:
If meaningful additional gains require changing RNG consumption order, floating-point reduction order, common-random-number strategy, parallel decomposition, or another implementation detail that may make outputs non-bit-identical while preserving the same 50,000-run probabilistic model, Research/Performance must first define and pass a deterministic reproducibility + statistical-equivalence contract. Do not treat “bitwise different” as automatically wrong, but do not relax exactness informally.

Not authorized merely for speed:
- reducing the canonical 50,000 iteration count;
- changing Forecast inputs/distributions;
- weakening lineup/scoring/standings/playoff fidelity;
- approximating changed-State Simulation without explicit separate authority;
- silently changing RNG/model semantics;
- moving analytical work into frontend presentation;
- paying for materially larger infrastructure before software-efficiency evidence is exhausted and Management explicitly approves cost.

The objective is end-to-end faster **fresh** Simulation while preserving analytical quality, reproducibility, and authority—not just faster cache hits.

## 2026-09-26 — Simulation count must be empirically justified; restore Multiverse analytics
Management does not treat 50,000 Monte Carlo runs as a mathematically privileged constant. It remains the current canonical production setting until an empirical convergence study demonstrates a better cost/precision contract.

The prior FSFFL system used smaller development runs and 50,000-run final/production confirmation; this was a conservative production convention rather than evidence of a universal 50,000-run accuracy breakpoint.

Before changing the canonical run count, Performance/Simulation Research must evaluate convergence across representative league States and changed-State scenarios. At minimum compare 5k, 10k, 20k, 25k, 35k, 50k, 75k and 100k against a substantially larger offline reference run where feasible. Use multiple independent seeds and paired/common-random-number comparisons where appropriate.

Evaluate:
- expected wins and wins variance;
- playoff, first-place and championship probabilities;
- finish-rank distributions;
- team ordering/rank stability;
- changed-State/trade deltas, especially sign and action-threshold stability;
- tail/rare-event estimates;
- runtime, CPU and memory cost.

Do not choose a count merely because aggregate probabilities look close. The governing question is whether decision-relevant outputs are stable enough that additional simulations have immaterial value. If a lower fixed count or a statistically governed adaptive stopping rule achieves the same decision precision, return it as a Management gate. No production count change is authorized yet.

Separately, Management directs recovery of the original FSFFL **Multiverse / Outlier Tracker** concept as a downstream Simulation analytics product. The legacy system preserved deterministic simulation IDs and surfaced model-consistent alternative futures such as:
- highest player week / season;
- unexpected superstar season;
- highest / lowest team week and season points;
- best / worst record;
- biggest margin;
- best team to miss the playoffs;
- rare champion / high-seed champion.

This layer must not alter Forecast or Simulation probabilities. It should consume the same canonical simulation pass where possible and preserve enough identity/replay provenance to audit a surfaced universe.

Important correction for the modern product: the single most extreme observation is sample-size dependent and should not be presented as a stable forecast. Prefer rarity/context labels, percentile or empirical-frequency context, and representative interesting universes alongside absolute extrema. These are plausible/model-consistent alternative futures, not predictions.

The Multiverse layer belongs downstream of Simulation in Analytics/Presentation and may later feed Home, League Atlas, Reports, season previews and shareable league storytelling.

## 2026-09-26 — Core runtime acceptance is not product-surface acceptance
Management physical testing invalidated the assumption that successful State-first Forecast/Simulation/Value/restart acceptance is sufficient to close app acceptance.

From now on, acceptance is layered:
1. **core runtime acceptance** — State/Forecast/Simulation/Value/authority/persistence;
2. **product capability acceptance** — Intrinsic/future forecast and other supported derived capabilities;
3. **surface acceptance** — actual hosted endpoint + rendered major surface behavior on target mobile/browser;
4. **readiness truth** — the shell status may summarize only what these accepted capabilities actually justify.

A lazy/derived endpoint that was not exercised cannot be inferred healthy from compatible inputs. “Intelligence current” must have explicit scope and a governed as-of timestamp; partial capabilities must remain visible rather than hidden behind a green core status.

## 2026-09-26 — vNext/P0 production coupling is a charter non-conformance
Management classifies the current vNext production dependency on P0-specific runtime/materialization code as an architectural non-conformance with the FSFFL NEXT charter.

The underlying mathematical reuse is not itself prohibited. A previously validated identity map, probability layer, or other primitive may remain authoritative if evidence still supports it. The violation is allowing a promoted vNext production adapter to depend directly on a prior model's implementation boundary such that changes/fixes to that prior path do not automatically apply to the active model.

Charter-correct target:
- reusable validated primitives live behind model-neutral Forecast contracts/services;
- vNext owns its complete subject-scoped production adapter;
- P0 remains provenance/history/reference, not an implicit runtime owner of vNext behavior;
- downstream Intrinsic/Value/Presentation consume the stable Forecast contract and do not know whether P0, A2, Burr, or a future challenger supplied an internal component;
- replacing/promoting a Forecast model should not require downstream product rewrites and should not leave hidden dependencies on superseded model-specific code.

The immediate corrective must therefore do more than duplicate another subject filter. Extract or introduce the smallest model-neutral reusable boundary needed to eliminate the direct P0-specific production dependency while preserving validated numerical authority.

Implementation must also audit the active vNext production path for similar hidden inheritance/coupling before re-promotion. Do not broaden this into an unrelated rewrite; fix the violated abstraction boundary and add regression/architecture tests that prevent recurrence.

## 2026-09-26 — Reject all-or-nothing long-horizon fallback interpretation

Management rejects the interpretation that a single position × horizon catastrophe on the sealed holdout justifies reverting the entire Y4-Y8 architecture to the incumbent `specialist|forecast10|two_part_ridge` baseline.

The prior holdout result remains valid evidence:
- the frozen richer architecture as a whole failed its predeclared confirmation rule because QB Y8 RMSE materially regressed;
- no post-hoc repair of that exact frozen candidate may be presented as if it passed the original untouched holdout;
- the QB Y8 failure is real and must remain visible.

However, the incumbent fallback is a **baseline/comparator, not presumptive authority**. It was first, not proven globally optimal. The original comprehensive directive explicitly allowed different models/features by position and horizon when empirically justified.

Research must therefore distinguish:
1. **global architecture rejection** — the frozen 75/25 architecture did not earn blanket promotion;
2. **cell/route evidence** — individual position × horizon cells may still support different models or feature sets;
3. **fallback authority** — no cell inherits the incumbent merely because the global candidate failed elsewhere.

The next Research design must permit position × horizon-specific routing, shrinkage/pooling, or explicit coarse/uncertain representation where evidence supports it. It must not use the already-seen final holdout to hand-pick a QB Y8 replacement. Instead, define a new general routing/selection policy using development chronology / repeated outer rolling validation / stability penalties and then evaluate that policy honestly with the remaining defensible historical evidence. If no truly untouched Y8 season remains, state that limitation explicitly and do not relabel reused evidence as untouched.

Production H3 remains unchanged. No Y4-Y8 implementation is authorized.

## 2026-09-26 — Legacy activation coverage does not define current Intrinsic availability
Management determines that the frozen activation-bundle coverage flags for injury/practice, participation/snaps, roster continuity, and similar completed-source evidence are **provenance metadata**, not automatic current-production availability gates for the vNext Intrinsic contract.

The current production Intrinsic path is governed by preserved Year-1 Forecast authority, the FutureForecastContract, league scoring compatibility, governed subject coverage, and the frozen Shapley/Value contract. Missing optional/legacy evidence families may be disclosed as evidence richness limitations but must not downgrade an otherwise complete authorized Intrinsic contract.

Fail-closed behavior remains mandatory for genuinely required current inputs.

## 2026-09-26 — Intrinsic recomputation policy is dependency-scoped
Management establishes that FSFFL Intrinsic must be recomputed only when an **authoritative input actually consumed by the Intrinsic calculation changes**. A new canonical LeagueState ID by itself is not sufficient reason to invalidate Intrinsic.

A cold Intrinsic recomputation is required when any of the following materially changes:
- preserved governed Year-1 Forecast evidence/content or its authoritative source/model coordinate;
- the governed FutureForecastContract content, model version, subject universe, or scoring coordinate;
- league rules consumed by Shapley economics, including scoring, lineup/capacity structure, or team count;
- evaluation season / season rollover;
- Intrinsic/Shapley contract version or governed numerical parameters such as discount, permutations, seed, or other authorized model settings;
- any other future dependency only after it is explicitly promoted as a required Intrinsic input.

A cold recomputation is **not** triggered merely by:
- roster ownership / trades / waivers;
- standings, matchup results, points scored/against;
- draft-pick ownership, FAAB, team labels, owner labels;
- ordinary canonical State refresh timestamps/provenance;
- injury/practice, participation/snaps, roster-continuity or player-status metadata unless a future authorized Intrinsic model explicitly consumes them;
- switching away from and back to a league when a compatible persisted Intrinsic artifact already exists.

Operational policy:
- compute/persist Intrinsic proactively in the background when a true dependency changes;
- preserve and expose the last-good Intrinsic with its governed as-of/compatibility status while a genuinely new contract is building, without claiming stale evidence is current;
- once the new contract completes, atomically promote it;
- routine product opens, league switches and Refresh Intelligence should hit the compatible persisted artifact and return near-immediately.

This policy preserves point-in-time provenance separately from computational compatibility. Exact State identity remains authoritative for evidence history; it is not itself the Intrinsic cache key.

## 2026-09-26 — Football-state changes propagate through Forecast before Intrinsic
Management clarifies the dependency-scoped Intrinsic recomputation policy.

A fantasy-league ownership change does not by itself change player Intrinsic. An NFL-context change can.

Events such as NFL injury, return from injury, NFL trade, release/cut, signing, depth-chart promotion/demotion, role/opportunity change, suspension, or retirement status must trigger **Forecast reevaluation** when authoritative current evidence changes. Intrinsic then recomputes only if the governed Forecast inputs/contracts consumed by Intrinsic materially change.

Authority sequence remains:
`Point-in-Time State / governed football evidence → Forecast → Intrinsic/Value`.

Implementation must not hard-code arbitrary injury, trade, cut, or depth-chart penalties inside Intrinsic.

Current limitation: the deployed vNext Y2/Y3 contract is intentionally based on a frozen 2026 source coordinate and does not yet have a fully governed live football-state update layer for all such events. This is a Forecast freshness limitation, not permission to ignore the events. Research must determine the governed in-season update mechanism, while Implementation must make cache compatibility depend on Forecast output identity so any future authorized Forecast update automatically invalidates Intrinsic.

## 2026-09-26 — Injury effects split temporary availability from structural dynasty impact
Management establishes the conceptual treatment for injuries in Forecast → Intrinsic.

A temporary injury must not be interpreted as a generic reduction in player quality. Forecast should decompose:
1. **current-season availability / games missed**;
2. **conditional production when active**;
3. **role/opportunity after return**;
4. **durable survival / career-trajectory effect**, if supported by evidence.

For a short-duration injury with expected full recovery:
- current-season expected points should fall in proportion to expected missed availability;
- conditional healthy production and Y2/Y3 trajectory should remain substantially unchanged unless evidence supports otherwise;
- Intrinsic should therefore fall modestly through the affected current-season contribution, not collapse across all horizons.

For injuries with meaningful recurrence, recovery, role-loss, or career-longevity evidence, Forecast may also revise conditional production and/or future survival/role probabilities. The size and persistence of that adjustment must be empirically governed by injury type/severity/position/age and horizon, not a hand-coded dynasty penalty.

Return from injury reverses the temporary availability effect as current evidence improves; structural effects persist only to the extent supported by governed evidence.

This policy belongs to Forecast. Intrinsic consumes the resulting multi-horizon Forecast and must not separately apply a second injury penalty.

### Remaining-season basis for temporary injury effects
For in-season valuation, temporary availability shocks must be applied to **remaining current-season expected utility from the evaluation date**, not retroactively to already-realized games. Already-completed production is historical evidence; it is not future asset utility. As the season progresses, the maximum current-season injury impact on dynasty Intrinsic naturally shrinks because less Y1 utility remains at risk.


## 2026-09-30 — Simulation batched-Gaussian experimental gate APPROVED
Management approves an **experimental, versioned non-bit-identical RNG branch and equivalence study** for batched NumPy/PCG64 normal draws at the unchanged 50,000-trial production count.

This approval does **not** authorize production adoption, merge to main, or deployment of the changed RNG protocol.

Required boundaries:
- preserve the existing Normal(mean, stddev) model semantics, zero floor, independence assumptions, weekly scoring inputs, standings/playoff rules, output fields, and Simulation authority;
- add explicit engine/RNG protocol identity and deterministic replay provenance so old Python-RNG artifacts cannot be confused with the new protocol;
- retain the current Python Random.gauss replay path for existing manifests;
- keep 50,000 canonical production trials;
- pre-register and execute the proposed equivalence study across at least 100 independent root seeds × 50,000 trials per engine, using the proposed margins as the initial acceptance contract: ±0.002 absolute for ordinary per-team probabilities, ±0.001 expected wins, and ±0.005 rank-distribution total-variation distance, plus the stated tail/downstream/resource checks;
- any systematic downstream Decision/Search/Optimization behavior change, material tail undercoverage, replay instability, or unacceptable Render memory/foreground regression blocks adoption.

After the experimental study, return to Management with measured runtime/resource benefit and full equivalence evidence for a separate production-adoption decision.


## 2026-09-30 — Simulation RNG practical-materiality gate: proceed to downstream + hosted validation
Management reviewed PR #311's completed 100-root-seed × 50,000-trial experiment and explicitly **does not require a large brute-force extension solely to force proof of the original ±0.001 expected-wins margin** before continuing the adoption evaluation.

The original statistical result remains exactly what it was and must not be relabeled:
- expected-wins equivalence at ±0.001 was **not established**;
- the worst observed point difference was +0.002395 wins;
- its simultaneous interval was [-0.002201, +0.006991];
- all 12 intervals included zero;
- playoff/first-place/championship probability margins passed;
- rank-distribution TV margins passed;
- expected-wins team order had zero pairwise inversions.

Management interpretation: the observed expected-wins effect size is practically negligible in isolation, while the unresolved questions with potential product consequence are **downstream decision behavior and constrained hosted execution**. The ±0.001 result remains part of the evidence package, but it is no longer the sole controlling gate.

Authorized next work on PR #311:
1. Preserve 50,000 trials, all Simulation/Forecast/Value/Decision semantics, explicit RNG/replay versioning, and the legacy Python replay path.
2. Do **not** launch a thousands-of-seeds study merely to satisfy ±0.001. A bounded confirmatory statistical run is permitted only if Work first documents why it is useful for detecting directional drift or another concrete risk; it must not be used to retroactively redefine the original study as a pass.
3. Run the missing changed-State downstream validation across representative scenarios, including clear cases and near-boundary cases. Compare Team Utility, Value/Analytics consumers, Decision direction/sign, Search/Optimization candidate sets/order, and any user-visible recommendation/frontier consequences. Any systematic or materially consequential change outside documented Monte Carlo/tie uncertainty blocks adoption.
4. After local/downstream validation is clean and exact-head CI/review are green, Management authorizes a **controlled, reversible hosted validation deployment** of the experimental branch to the private-beta Render service for measurement only. This is not production adoption and does not authorize merge to main. Measure the full 50k Simulation phase, total refresh, heavy-work wait, peak RSS/headroom, foreground Home/My Team/Product Context responsiveness, publication/readiness, and restart behavior. Prefer batch 500 unless new evidence supports another bounded batch.
5. If hosted/downstream validation passes, return to Management for the separate final production-adoption decision. If it fails, restore the prior production deployment and report the concrete blocker.
6. Before final validation, reconcile/rebase PR #311 with current main without truncating or replacing canonical operations histories.

After this RNG candidate decision, re-profile the full hosted Simulation path before ordering the next optimization tranche. The broader Simulation modernization remains active regardless of whether this RNG candidate is ultimately adopted.


## 2026-09-30 — PR #311 hosted resource gate: adoption withheld, bounded memory attribution authorized
Management reviewed the controlled private-beta Render validation of PR #311.

Result:
- the NumPy/PCG64 batch-500 candidate completed Forecast, Simulation, Value, Intrinsic and atomic publication at 50,000 trials;
- downstream changed-State validation and replay/persistence evidence remain acceptable;
- the original expected-wins ±0.001 study remains **inconclusive** and is not relabeled;
- hosted end-to-end publication took about 256.7s;
- the Forecast-complete → Simulation-complete phase boundary was about 59.0s;
- process high-water RSS reached 576,552,960 bytes against the unchanged 536,870,900-byte hard limit;
- no unexpected restart/OOM occurred, but the resource gate failed;
- available telemetry does **not** isolate the transient peak to the NumPy kernel, player history, Forecast, or another single owner.

Management decision:
1. Production adoption remains withheld. Do not merge PR #311 to main yet.
2. Authorize one **bounded memory-peak attribution and correction pass** on the same branch/workstream. The goal is to identify the short-lived allocation owner(s) responsible for the ~39.7 MB hard-limit overage and remove avoidable overlap/retention without changing Forecast/Simulation/Value semantics, 50,000 trials, modeled distributions, or accepted lifecycle authority.
3. Prefer instrumentation, lifetime/ownership fixes, staged release/reclaim, bounded batch/object reuse, and duplicate-work elimination before any capacity or model-fidelity change.
4. Do not broadly reopen runtime architecture. If the peak cannot be safely reduced under the existing free-tier hard limit with a narrow correction, stop and return to Management for a capacity decision rather than layering on more complexity.
5. After a narrow correction, rerun the same controlled batch-500 hosted journey with true concurrent Home/My Team/Product Context reads, full readiness/publication, restart restoration, exact RSS/high-water evidence, and rollback to main afterward.
6. A later separate Management decision controls production adoption.


## 2026-09-30 — PR #311 memory corrective should advance Simulation 2.0 where attribution supports it
Management refines the bounded memory-corrective directive for PR #311.

Do **not** treat the 576.6 MB hosted high-water mark as a request for an isolated 40 MB micro-patch. First determine whether the transient peak is caused by a representation/lifetime boundary that the already-authorized Simulation 2.0 roadmap is intended to replace: duplicated Forecast-derived stochastic inputs, parallel Python-object and compact representations, repeated lineup/scoring structures, oversized temporary arrays, serialization/object-model duplication, or delayed release across the Forecast → compiled Simulation state boundary.

If attribution supports that class, implement the smallest production-worthy Simulation 2.0 primitive now rather than creating parallel technical debt. Preferred roadmap-aligned mechanisms include:
- one reusable compiled/indexed Simulation state built from governed Forecast evidence;
- compact numeric/indexed representations instead of repeated dict/Pydantic traversal inside the engine;
- explicit release/reclaim of superseded Forecast-to-Simulation intermediates once the compiled state owns the needed inputs;
- bounded/preallocated/reused batch buffers;
- invariant lineup/scoring structures constructed once and reused;
- elimination of duplicate stochastic/input materialization;
- reduced repeated serialization/object construction where authority does not require it.

This remains a bounded tranche, not authorization to rewrite the entire engine. Preserve 50,000 trials, Forecast/Simulation/Value authority, modeled distributions, replay/version identity, legacy Python replay, downstream contracts, and current product semantics.

If instrumentation proves the peak is independent of Simulation 2.0 (for example a Forecast- or player-history-only allocation with no cross-boundary duplication), fix that owner narrowly instead.

After the smallest evidence-backed correction, rerun exact-head CI/review and the reversible batch-500 hosted journey with true concurrent foreground reads, full readiness/publication, restart restore, exact high-water evidence, and rollback to main. If the unchanged free-tier hard limit still cannot be met without broad architecture/fidelity changes, return to Management for a capacity decision.

## 2026-10-01 — PR #311 hosted concurrency gate: use an external acceptance runner, not Work browser
Management accepts the exact-head PR #311 code/review state as ready for the final hosted measurement. The remaining blocker is Work Mode browser URL policy, not a product defect.

Decision:
1. Do not wait on or weaken the required concurrent foreground-read gate.
2. Execute the final reversible batch-500 Render validation using a platform-approved **external acceptance runner** (prefer a short-lived GitHub Actions job or equivalent repo-owned client) that can issue real concurrent HTTP requests to the public private-beta host during refresh.
3. The runner must exercise Home, My Team and Product Context concurrently against the actual deployed Render service, not substitute in-process route calls or sequential probes.
4. Use only existing secure authentication/session mechanisms; do not place credentials/tokens in repo content or logs. If no supported noninteractive authenticated path exists, stop at INPUT GATE and request the smallest user action needed.
5. Preserve all existing hosted gates: 50,000 trials, batch 500, exact process high-water RSS, full readiness/publication, restart restoration, and rollback to main.
6. If memory exceeds 536,870,900 bytes, return to Management for capacity. If the hosted run passes, return immediately for the production-adoption decision; do not add another generic validation cycle.
