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
