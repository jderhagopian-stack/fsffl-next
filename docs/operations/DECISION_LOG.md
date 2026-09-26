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
