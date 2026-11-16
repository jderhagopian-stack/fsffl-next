# Trade Center presentation

Trade Center shows one recommendation for the exact package, followed by what changes for both teams. Use the compact teal cards and readable spacing used in Explore.

## Visible structure

1. A builder for players and picks. It starts open, folds after analysis, and reopens through “Adjust package” or its own summary. Moving the existing controls preserves their selection and event handlers.
2. One recommendation with a short explanation. Copy the returned Decision; never derive a replacement recommendation in the browser. Show “Preliminary” while evaluation is pending and name actual missing inputs when incomplete.
3. The assets each side sends, then the user's chosen or suggested focus when returned.
4. One bilateral table: expected wins, playoff chance changes in percentage points, and separate cut-adjusted 3-Year and Career raw contribution. Match each side by team ID. Missing/nonfinite/incomplete native evidence stays a dash; zero stays zero. Never substitute market value or sum the overlapping horizons.
5. Five expandable sections: market value and cuts, lineup by position, season outlook, recommendation reasons and the other team's case. Lineup totals are labeled as totals over their projection period, not points/week.
6. Adjust-package and applicable counteroffer actions, followed by calculation details.

## Language

Explain effects and choices in normal language: “playoff chances”, “less projected depth”, “picks received”, and “what you give up”. Avoid exposing internal module numbers, authority terminology, promoted drivers, bilateral shapes or generic disclaimers in the main experience. Translate existing results; do not invent owner motives, acceptance probabilities or certainty about surplus. Distinguish suggested priorities from user-selected priorities. Preserve meaningful missing-data warnings and actual costs.

Existing older renderers remain behind the established compatibility boundary; the recomposition owns the single visible result and hides redundant summaries. Do not add a new presentation overlay or duplicate computation. This redesign makes no changes to valuation, Decision policy, Forecast, Simulation, search, persistence or API contracts.

## Football-first explanations

The user should not have to assemble the conclusion from a list of model fields. Explain the particular football exchange: named incoming players who enter the lineup, production lost elsewhere, the actual player taking over an outgoing starter's slot, existing positional weakness when a matching league comparison proves it, and the trade's effect on the season and future assets. Summarize the focal case in the hero and use the expandable reasons for supporting roster detail. Explain the other team in their own perspective; never call their outgoing players “you send”.

Use the returned competitive-state classification without equating it with an owner's wishes. Explicit user goals remain distinct. No automatic three-horizon list is presented as insight. A future-focused trade can be sensible for a contender; explanations preserve both the benefits and the short-term costs without changing the authoritative recommendation.

A projected bench role does not prove surplus, a tiny raw positive does not prove a meaningful gain, and an incoming player need not enter the lineup. Name cuts where required. Do not invent acceptance, owner motives, certainty about injury/bye cover, or reference-anchor significance. Current/championship/first-place outcomes remain separate. Use matching State and forecast-period positional evidence; if a role or replacement is unavailable, omit the unsupported claim.

Published league-relative strength is reused only when the source State, forecast horizon/as-of, full optimized assignments, bench IDs and per-position points match the current comparison. No new optimization, Simulation, provider request or persistence is added for narrative generation. The formatter consumes facts; it does not assign a score, materiality threshold or recommendation.

## Marginal lineup replacements

Explain the difference between the before/after **sets of starting players**, not numerical WR1/WR2 or slot reordering. An existing starter moving from FLEX to WR does not supply new production. Include every affected position when a different-position bench player enters through FLEX/Superflex. Describe actual entrants, where they start, and who leaves the lineup. Do not fabricate a one-to-one replacement in a multi-asset trade. Preserve unfilled slots and cut/demotion distinctions. Legacy slot-movement fields remain for compatibility but no longer drive replacement prose.

## Counteroffer review

The quick and deep frontier keep their four/24 evaluation limits and canonical owned packages. A request reads the existing published native source once for the two rosters, then reuses Explore's accepted preliminary roster/economic/priority screen. No full season Simulation, provider acquisition or persistence work is added. Default inferred goals and explicit instructions use the same owner assessment as Explore.

Compare each team's Current, 3-Year and Career changes against the original package in its own units. An original negative may shrink or disappear, while a different cost can emerge or deepen; explain both. Never combine the horizons, invent a universal repair score, or call this a final recommendation. Qualified counters remain preliminary and load into the existing guarded builder for explicit full analysis. Missing native evidence cannot become a claimed future-aware counter just because the legacy roster-only classifier was positive.

### Targeted counteroffer search

When matching published native horizons are available, counter search may replace
one offered asset with another owned player or pick without enlarging a package.
At least one original incoming target remains; abandoning the sole target is a
different search. Protected managed-team players remain excluded.

Search interleaves separate questions for each team's known Current, 3-Year and
Career losses. Current-loss hypotheses try retaining a traded baseline starter
and using bench/pick compensation. Native-horizon hypotheses try closing the
original loss with minimal extra compensation within that horizon, then partial
repairs. Smaller structural alternatives remain a separate lane. No horizons or
teams are blended into a score. Baseline starters come from the governed optimizer,
so FLEX/Superflex and league-specific starting requirements are respected without
assuming that a nominal WR rank defines who is expendable.

These inexpensive hypotheses omit cuts, future lineup interactions and weekly
schedule effects. They are never presented as transaction consequences. Every
selected package still receives the existing preliminary lineup/legality/native
horizon/priority evaluation and comparison against the original deal. Bench
players are not assumed worthless. A search hint cannot create a recommendation,
owner willingness estimate or Simulation result. Missing published evidence uses
the existing diagnostic path. Four quick /24 expanded evaluation limits remain;
this is a bounded local search, not proof that no better league-wide deal exists.
