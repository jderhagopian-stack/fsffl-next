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
