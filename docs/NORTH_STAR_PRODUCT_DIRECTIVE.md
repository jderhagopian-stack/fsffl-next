# FSFFL NEXT — North Star Product Directive

The North Star mockup is the product target, not a loose source of inspiration.

FSFFL NEXT should feel simple and visually rich on the surface while remaining extremely deep underneath. Governed analytical sophistication powers the interface; it does not dominate the default interface.

## Default experience

The first read prioritizes graphical information, compact visual comparison, obvious numerical hierarchy, clear strengths and weaknesses, player and franchise identity, concise interpretation, and actionable next steps. A user should understand most of a screen by scanning it.

Consumer language leads. Examples:

- `WR #1 of 12 — strongest WR room in the league` is the product statement.
- exact position-strength index, source/version and methodology are supporting detail.
- `83% playoff chance` leads; Simulation provenance belongs underneath.

## Drill-down experience

Tap/click should reveal deeper FSFFL intelligence where appropriate: projections and sources, league-relative measurements, Value evidence, optimized lineups, replacement exposure, Simulation distributions, trade consequences, package economics, counterparty perspective, Behavioral evidence, historical evidence, provenance and methodology.

Analytical depth is preserved and moved to the correct interaction depth.

## Visual language

Default toward visual representation when it makes comparison or interpretation faster:

- charts and ranked bands;
- progress and strength bars;
- rings/gauges where useful;
- compact comparison graphics;
- graphical league maps;
- player and asset identity;
- strong numeric typography;
- status, risk and action indicators;
- purposeful icons;
- restrained cards;
- short visual narratives instead of long explanatory prose.

Do not force every metric into a graph.

## Information compression

Age, pick capital, fragility, positional strength and similar league-wide intelligence should avoid long mobile lists when a heat map, ranked chart, distribution, top/bottom summary, comparison band, expandable detail, or owner/team drilldown communicates the same governed information faster.

Preserve the underlying information and evidence. Reduce cognitive and scrolling burden.

## Surface targets

### Home

Home is a live personalized command center. Its dominant region should normally contain a real persisted/current insight or opportunity rather than instructions to open another surface first. Home answers: **what matters now and what should I do next?**

### Franchise

Franchise is a graphical diagnosis of one team: compact position visualization, player identity, roster construction, age/draft-capital trajectory, risk and optionality, with exact measurements available on tap.

### League

League is a visual league map/atlas. Users should visually discover positional monopolies, weak rooms, contenders/rebuilders, young/old teams, pick wealth, depth/fragility and complementary trade partners before opening exact numbers.

### Market

Market is a personalized opportunity experience. It should surface realistic, contextual, actionable opportunities with visual fit and consequence summaries, while preserving Search and Decision authority boundaries.

### Trade Center

Trade Center is a decision/simulation workspace with clear visual before/after outcomes, both-team consequences, package economics, league impact and drill-down evidence.

### Owner Intelligence

Owner Intelligence is a behavioral dossier: visual patterns and tendencies first, source-backed Behavioral evidence underneath. It must not create universal Value or fake acceptance probability.

## Product choice rule

When choosing between showing more analytical output and communicating the important intelligence better, choose communication for the default experience and expose the deeper analytical output through drill-down.

## Architecture remains unchanged

The governed pipeline and authority boundaries remain authoritative:

`Data → State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Presentation may organize, compress, visualize and explain governed truth. It may not create hidden composite/master scores, acceptance probabilities, Search-created Decision truth, Behavioral contamination of universal Value, arbitrary model multipliers, or presentation-created recommendations.


## What-If / Counterfactual Intelligence

What-If is a generalized counterfactual decision surface, not merely a current-roster stress test.

It must support two distinct modes:

### Forward counterfactual
Start from the current canonical State, change one or more explicit decisions/assumptions, then recompute only the governed downstream consequences. Examples include a trade, player availability, draft selection, waiver/add-drop decision, roster move, or other bounded hypothetical.

### Historical counterfactual
Start from an authentic point-in-time historical State, replace a real past decision with a specified alternative, and reconstruct what could have followed without leaking later information into the decision point.

Historical counterfactual analysis should preserve and distinguish at least two valid lenses:

1. **Point-in-time probabilistic lens — “What could reasonably have happened from there?”**
   - use only State, Forecast, Value, Decision evidence, uncertainty and owner/league information that was available at that historical cutoff;
   - branch the historical State at the decision;
   - simulate forward from the alternate branch using the governed model appropriate to that evidence horizon;
   - compare the alternate distribution with the original decision’s point-in-time distribution.

2. **Realized-world replay lens — “Given what actually happened on the field afterward, what would this alternate decision have produced?”**
   - hold later exogenous NFL outcomes/schedule facts fixed where appropriate;
   - substitute the alternate ownership/roster/draft decision;
   - replay downstream fantasy scoring, standings, lineup opportunities and league outcomes;
   - clearly label this as hindsight replay rather than information that was knowable at the original decision point.

Do not blend these lenses. A decision can have been rational at the time and still have produced a worse realized outcome, or irrational at the time and still have worked out. What-If must preserve that distinction.

The long-term counterfactual engine should be capable of branching from transactions, draft selections, waiver/add-drop decisions, lineup/availability decisions and other historically reconstructable league actions when evidence is sufficient. Multi-step/cascading counterfactuals may be added later, but must retain explicit lineage and avoid pretending unknowable downstream human decisions are deterministic.

The current production What-If implementation (single-player current-availability stress test) is an intentionally narrow first slice and must not be treated as the complete North Star definition.


## Strategic product-development filter

FSFFL NEXT is not a collection of fantasy calculators. The product is a **persistent intelligence model of a real fantasy league**. Every major surface should feel like a different question asked of the same governed league model.

Future roadmap choices should be evaluated against three tests. A proposed capability should materially do at least one of the following:
1. **Strengthen the persistent league model** — improve State, Forecast, Value, Decision, Owner Intelligence, historical lineage, uncertainty, or counterfactual understanding shared across surfaces.
2. **Make league intelligence easier to use** — reduce time-to-value, simplify a real user job, improve explanation/trust, or turn governed evidence into an obvious next action.
3. **Make the league itself more valuable/shareable** — deepen franchise/owner identity, history, rivalries, records, stories, social participation, or artifacts that naturally bring additional league members into the product.

Capabilities that do none of these should normally remain behind higher-value work.

### Product experience principle
Keep the analytical architecture deep and explicit internally, but make the default consumer experience simple. Users should not need to understand the authority pipeline to benefit from it.

Internal truth remains:
`Data → State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Consumer questions should feel closer to:
- What should I know?
- What should I do?
- Why?
- What happens if I do it?
- What did this look like then?
- What could have happened instead?
- What does this owner tend to do?
- What is happening in the history of this league?

Every material conclusion should support a bounded “why/evidence” drill-down rather than requiring technical knowledge up front.

### Time-to-value is a product requirement
The critical commercial workflow is:
`connect/select/sync league → current canonical State → reuse/rebuild governed intelligence → truthful readiness → useful answer`.

League connection, league switching, and Refresh Intelligence are therefore first-class product behavior, not implementation plumbing. A sophisticated downstream capability has little product value if the user cannot reliably reach current intelligence.

### Shared capabilities, not isolated features
Owner Intelligence, historical persistence, counterfactual state, Forecast provenance, league-specific behavior, and Value coordinates are shared infrastructure. They should be designed so multiple surfaces can consume the same governed evidence:
- Owner Intelligence can inform Market, Trade Center, future Mock Draft, Record Book/franchise history and counterfactual plausibility without contaminating universal Value.
- Historical persistence should support Record Book, historical trade analysis, historical What-If, owner/franchise identity and future draft/decision replay.
- Counterfactual State should support Trade Center, current What-If, historical What-If, draft alternatives and other bounded decision scenarios.
- League identity/history should be useful both analytically and socially.

### Breadth follows reliability
The intended roadmap remains broad, including deeper Record Book/history, generalized What-If, behavioral/needs-aware Mock Draft, Owner Intelligence, Simulator and other league-intelligence surfaces. Do not accelerate those at the expense of a reliable core.

Before materially expanding breadth, prioritize:
1. bulletproof league lifecycle and truthful readiness;
2. governed intelligence completeness;
3. high-quality and responsive Market/opportunity discovery;
4. a unified product experience across existing core surfaces.

This principle sharpens sequencing; it does not cancel already accepted long-term product intent.

### Commercial differentiation principle
Do not position FSFFL around a claim that an individual feature is unique. Many individual capabilities exist elsewhere.

The intended differentiation is the integration of:
- canonical football Forecast;
- league-specific scoring;
- separate Broad Market / FSFFL Intrinsic / League Market / Team Utility dimensions;
- Owner Intelligence;
- point-in-time historical evidence;
- Search and bilateral Decision;
- targeted Simulation;
- forward and historical counterfactuals;
- franchise/league history and identity;
- future behavior/needs-aware draft simulation;

all operating against the same governed league model with provenance and uncertainty preserved.

The goal is for users to experience one system that **knows their league**, not a navigation menu full of unrelated tools.
