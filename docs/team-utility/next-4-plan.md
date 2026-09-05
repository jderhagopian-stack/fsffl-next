# NEXT-4 Team Utility & Simulation Plan

NEXT-4 answers: **What does this asset or roster actually do for this team?**

It consumes canonical point-in-time league state from NEXT-1, football forecasts from NEXT-2, and economic value representations from NEXT-3. It may not rewrite any upstream authority.

## Authority split

1. **Team state / lineup** — determine the best legal lineup from the actual roster and league rules.
2. **Replacement impact** — measure marginal player contribution by re-optimizing the same roster without that player. Do not substitute an arbitrary league-average starter.
3. **Competitive simulation** — estimate wins, playoff probability, title probability, floor/upside and fragility from forecast distributions.
4. **Franchise utility** — combine competitive impact with future asset strength, depth, resilience and optionality without re-counting NEXT-3 market value.
5. **Strategic posture** — owner preference remains separate from calculated team state and may be applied downstream without changing calculated reality.

## First implementation milestone

The first slice is deliberately narrow and authoritative:

- deterministic lineup optimization under canonical lineup requirements;
- FLEX and SUPERFLEX eligibility derived from position, not hardcoded player premiums;
- taxi and IR excluded from active lineup availability;
- missing forecast evidence surfaced rather than silently imputed;
- marginal lineup impact measured against the team's actual optimized replacement path;
- no simulation, trade recommendation or owner preference logic in the lineup layer.

## Next slices

After the lineup/replacement foundation passes tests:

- add uncertainty-aware team scoring distributions and correlation-aware simulation inputs;
- construct league-wide weekly/season simulation with reproducible random seeds and 50,000 trials when computationally reasonable;
- derive competitive-state outputs (expected wins, playoff/title probability, fragility);
- add team-specific franchise utility as a distinct typed output;
- add explicit calculated-state vs owner-strategy contracts;
- produce a reproducible Team Utility Report for every team in a league;
- run sanity calibration before NEXT-4 exit review.

## Anti-double-counting rule

A real-world effect enters final team utility once. NEXT-3 market/scarcity economics are consumed as upstream economic evidence; NEXT-4 adds only the team-specific roster and competitive consequence. A QB cannot receive a generic Superflex bonus here merely because the market already values Superflex scarcity.
