# FSFFL NEXT — North Star Surface Gap Analysis

Date: 2026-09-20
Baseline: deployed/main `a3c8a65e45b484b342ad3b4351cc8d8d81811971`

This analysis compares the actual current product against the North Star directive and Phase 3 acceptance standard. It does not create new model authority.

## Home — "What matters right now?"

**Current job:** priority and recency; answer what deserves attention.

**Current implementation:** scan-first Home experience already combines competitive outlook, roster pressure/risk, opportunity handoff, league comparison and workflow shortcuts. The shell/navigation has already been reorganized around Home / Franchise / League / Market / More.

**North Star gap:** the strongest remaining gap is not another metric card. It is a governed "what changed since last visit" / priority feed and a durable product-learning loop. Current Home correctly avoids inventing change history or launching expensive deep Search merely to fill the page.

**Missing governed input:** previous-distinct-State / change-feed contract.

**Composition gap:** some residual technical/runtime status and duplicated Franchise detail can still be demoted as product learning identifies what owners actually use.

**Mobile / latency:** current lightweight Home can proceed; change feed is evidence/backend blocked.

**Can proceed now?** Minor composition work can, but the most valuable missing capability is blocked on governed previous-state evidence.

## Franchise — "What is actually driving my team?"

**Current job:** diagnosis, roster construction, strengths/weaknesses, fragility, core assets, optionality, picks.

**Current implementation:** dedicated Franchise shell, positional strength/pressure, lineup engine, fragility, core asset/nonstarter optionality, age shape, draft-capital trajectory, roster subviews and a lazy Value Lens separating Broad Market, FSFFL Intrinsic, unavailable League Market and Team Utility.

**North Star gap:** the information is largely present. Remaining work is composition refinement, reducing inventory-table dominance, and validating the short-term versus long-term story with beta use.

**Missing governed input:** mature age/value-duration and longer-horizon dynasty outlook remain limited; League Market Value remains unavailable.

**Mobile / latency:** lazy Intrinsic loading protects first paint. Existing diagnosis is suitable for continued beta validation.

**Can proceed now?** Yes for presentation refinement; no for unsupported duration or League Market inference.

## League — "How does this league fit together?"

**Current job:** league structure, positional monopolies/weak rooms, competitive lanes, age, depth/fragility, future capital and complementary needs.

**Current implementation:** current League page already contains competitive-state lanes, a central positional edge matrix, weakest-position/supply context, future-asset/pick structure, age tracks and depth detail. Legacy duplicate positional companion has been reduced to a compatibility shim.

**North Star gap:** League is much closer to an atlas than the old leaderboard, but complementary-partner interpretation can be made more obvious and repeated leaderboard/detail material can continue moving into drill-down. League Market Value remains correctly absent.

**Missing governed input:** League-specific price coordinate is blocked; complementary-needs presentation must remain descriptive and cannot become Search authority.

**Mobile / latency:** structural read can be presentation-only from existing governed outputs.

**Can proceed now?** Yes for atlas composition/drill-down; no for League Market Value.

## Market / Opportunities — "What moves are worth my attention?"

**Current job:** intent-led discovery with clear authority state and a path into deeper Decision.

**Current implementation:** Market Focus changes server-owned Search; quick workspace gives useful structural evidence first; full workspace adds bounded Decision enrichment; Search order is not a hidden composite score; Strongest FSFFL Opportunity and Closest Market Match remain distinct; detailed opportunity drill-down, trade handoff, waiver flow and PR #157 Intrinsic-vs-Broad-Market discovery are present.

**North Star gap:** the major previously documented Intrinsic-disagreement discovery gap is now closed. Remaining work is beta validation, continued visual compression, and watching for poor-target examples that trace to authoritative Search rather than patching presentation.

**Missing governed input:** no calibrated acceptance probability; League Market Value absent; owner-adjusted value absent.

**Mobile / latency:** quick path observed around 1–2.2s; full enriched workspace 14–19s cold, so progressive rendering is essential.

**Can proceed now?** Yes for product refinement and validation. Do not reintroduce full Decision work into first paint.

## Trade Center — "Does this deal make me better?"

**Current job:** bilateral decision room with package economics, roster/lineup consequences, Simulation, risk, next action and counters.

**Current implementation:** side-by-side package, quick package economics, pre-Simulation roster analysis, changed-state 50k Simulation, final disposition, upside/risk/next-action composition, counters/frontier, Behavioral proposal fit and methods drill-down.

**North Star gap:** product composition is substantially in place. The principal remaining customer problem is latency of a fresh 50k run, not missing UI truth. Some legacy explainer layers remain underneath the compressed Decision Room and can be removed after beta validation.

**Missing governed input:** acceptance probability remains unavailable by design.

**Mobile / latency:** quick view and analysis progressively reveal useful evidence; fresh full Simulation remains the known deep blocker.

**Can proceed now?** Presentation cleanup can; performance optimization waits for fresh current-SHA phase evidence.

## Owner Intelligence — "What does completed evidence say about this manager?"

**Current job:** owner dossier / negotiation intelligence.

**Current implementation:** dedicated owner selector and dossier with observed history, acquired/disposed positions, deal shapes, repeat counterparties, evidence dates/seasons, provenance and a strict inference-readiness boundary. Trade Center separately shows package-level directional Behavioral fit when governed.

**North Star gap:** this is the clearest remaining presentation gap. The page still leads quickly into a generic four-card count grid and repeated panels. The North Star calls for a scan-first owner dossier centered on observed patterns, relationships and evidence coverage, with raw counts secondary.

**Missing governed input:** context-controlled stable preference, recency/stability/confidence and calibrated acceptance remain evidence-blocked; the product must not fabricate them.

**Mobile / latency:** data volume is modest and already loaded through one Behavioral profile endpoint; a presentation-only recomposition does not require deep Search/Simulation.

**Can proceed now?** Yes. A bounded owner-dossier visual recomposition can use only existing observed evidence and is independent of Forecast-vNext.

## Cross-surface findings

- Product shell/navigation Slice A is already materially implemented.
- Home, Franchise, League, Market and Trade Center have already moved substantially toward the North Star family rather than remaining old-beta peers.
- The biggest engineering-performance issue is still fresh 50k Simulation; evidence for the exact current-SHA dominant subphase is not yet available.
- The clearest safe presentation slice is Owner Intelligence: improve hierarchy and visual grammar without inventing preference or acceptance truth.
- Product-quality review should follow Owner recomposition and continued beta validation, rather than starting another broad multi-surface redesign.
