# Conditional rookie forecasts and shared-game compatibility — 2026-11-14

Two additional checks are complete. A position/draft-capital forecast does not
beat the rank comparator on common observed rookies. Separately, a population
counterfactual confirms that adding entrants' allocations to incumbent values
from a different game can overcount contribution. Neither finding authorizes a
production model change, a redefinition of accepted Shapley, or a live defect claim.

## Conditional entry-level forecast

The pinned [nflverse NFL draft file](https://github.com/nflverse/nfldata/blob/7aaa66d2a71495b080ee79f6794ae23cc9396027/data/draft_picks.csv)
provides original NFL positions and overall draft picks. This avoids using today's
position labels or later NFL performance as entry features. On the QB/RB/WR/TE
source scope for 2014–2023 there are 759 drafted entries; 739 have usable canonical
identities. Twenty missing/conflicting identities remain unresolved, including two
direct-ID/PFR-crosswalk conflicts. No ambiguous identity is assigned zero.
This research scope is drafted NFL players at those original positions, not all
legal fantasy selections: undrafted players, NFL FB mappings and veterans require
separate treatment. The existing production player coverage is unchanged.

`scripts/evaluate_selected_rookie_prior.py` compares a position-only mean with a
positive-mean regression using original position, log NFL overall pick, and their
interactions. The Poisson regression link models a **continuous conditional mean**;
it does not assert Poisson outcome variance or supply a predictive distribution.
Regularization is selected from a frozen small grid using 2017–2020 chronological
selection folds; each fold's training labels mature before its draft year, and
all selection-fold labels mature before the 2023 target. No market prices,
current ages, later position changes, manually chosen player anchors, clipping or
post-target coefficient adjustments enter the model.

The final fit uses 558 canonical drafted entrants from 2014–2020. Of those, 250
contain at least one training-season absence handled under the explicitly labelled
[research assumption](native-pick-model-sensitivity.md), not a verified zero fact.
The incomplete source population and selective observed validation targets remain
material limitations. Both rule cases select regularization alpha 10; this is a
research result, not a promoted parameter or a reason to expand the search grid
after seeing the target. The source/evaluation scope remains fixed historical
fantasy points, not proven current league-scoring compatibility.

On the actual 2023 league draft, 25 selections are observable drafted rookies.
The other 11 ranks remain unscored by this conditional model; veteran/undrafted or
unobserved outcomes are not silently converted to rookie forecasts. Crucially,
this supplies the **actual selected identity** to the forecaster. It tests a
component that could eventually inform a selection mixture; it is not a forecast
of which player an unresolved future pick will select.

| Economic case | Targets | Position-only MAE | Position + draft-capital MAE |
|---|---:|---:|---:|
| 12-team, 3-WR Superflex | 25 | 127.66 | 108.46 |
| 1-QB counterfactual on the same selections | 25 | 117.00 | 104.09 |

That improves on a weak position-only comparator. It does **not** establish an
improvement over the earlier rank model. On the same 22 observed rookie ranks
supported by both methods:

| Economic case | Rank-smoothed MAE | Conditional capital MAE |
|---|---:|---:|
| Superflex | 101.34 | 102.89 |
| 1-QB counterfactual | 89.32 | 97.93 |

These are exploratory checks on a class already used in earlier research, not a
fresh untouched confirmation set. No winner is selected from named-player results.
The study took 17.43 seconds and 170,984 KiB peak RSS locally; no annual Shapley
recomputation was needed for this forecast study. No full Career value, joint
annual scenario, predictive interval or production eligibility is supplied.

## Source-population check

The richer raw-stat source and supplied panel both span 1999–2025, but the raw
source omits 716 RB player-season keys present in the panel. Of those panel rows,
701 have nonzero fantasy points. Thus the richer source cannot silently serve as
a complete zero/absence authority for the panel's universe. This does not prove
that every absent panel row is erroneous or that a current production method is
defective; it establishes a concrete source-population reconciliation requirement.
The research zero assumption used the supplied panel, not this narrower source.

## Live code trace and population compatibility

The accepted runtime calculates dynamic players **together** in the full
reference-plus-dynamic cohort. Its publication then deliberately preserves the
input reference rows and appends only the dynamic estimates, via
`append_dynamic_career_estimates` (`career-frozen-reference-append-v1`). This is
an accepted reference-comparison policy, not a joint allocation of one new game.
The [integration design](native-pick-integration-design.md) traces the merged
PR454 authority and preserves this behavior; the counterfactual below does not
establish that this accepted policy is invalid or require repricing players.

In `product/dynamic_career_composition.py`:
`_merge_candidate_inputs` combines the base and valid candidate Forecast rows,
then calls the unchanged full-cohort Shapley composer. The calculation does not value a candidate alone. Publication retains reference
rows while appending the complete expanded-game candidate results.
The future Forecast provider admits dynamic subjects from canonical State; this
review did not establish a separately governed future NFL-class population there.
This is a description of the traced path, not a conclusion that an accepted
method has been lost or that existing player values must be changed.

The integration question is whether a frozen historical/native pick prior and
current player estimates refer to compatible future economic environments. Equal
units and lineup rules alone do not establish equality of a cooperative game's
member population and forecasts. Existing football forecasts may already embody
future role competition; do not add another adjustment without tracing those
accepted effects. This study does not decide the correct production treatment.

A synthetic regression uses the production engine unchanged: two starting-QB
slots, incumbent forecasts 100 and 50, and an added future QB forecast of 100.
The incumbent-only grand utility is 150; the expanded game's grand utility is 200.
Adding the entrant's expanded-game allocation to old incumbent allocations exceeds
200. The accepted joint game remains internally consistent. This is a guard
against a naive integration, not an invented alternative valuation formula.

## Bounded historical population counterfactual

Necessity was established before computing: quantify the same compatibility issue
in a representative historical population. The saved **full 2023** three-WR annual
results were reused. Only two previously uncomputed incumbent-only games were run,
using explicit 2023 entry identities removed from the source population, with all
remaining forecasts/points and the accepted engine/permutations/seed unchanged.
This is hindsight fixed-points analysis, not historical point-in-time forecasting,
current-league scoring, a prediction of future entrants or a live refresh.

The full population has 587 players, including 95 explicit 2023 entrants
(11 QB / 27 RB / 39 WR / 18 TE); the reduced population has 492 incumbents.

| Economic case | Incumbent-only utility | Full utility | Entrant allocation in full game | Naively mixed total | Excess |
|---|---:|---:|---:|---:|---:|
| Superflex | 19,571.54 | 20,276.64 | 2,465.89 | 22,037.43 | 1,760.79 / 8.7% |
| 1-QB | 17,002.42 | 17,558.76 | 2,174.56 | 19,176.98 | 1,618.22 / 9.2% |

The two games took 5.99 seconds, peak 59,548 KiB locally. Shapley efficiency holds
within each game. The excess appears only when mixing allocations from different
populations. These are whole-universe demonstrations using all 95 entrants,
**not predicted bias for a live draft-pick portfolio or a particular trade**.
There is no native pick allocation in production today to which this percentage
can be attributed.

## Disposition

Do not promote either new forecast or compensate for these findings with display
scaling, market prices, arbitrary haircuts or repeated tuning. Retain the annual
frozen slot-release policy and existing player authority. Its compatibility with
evolving live player evidence needs an explicit approximation/authority contract;
this study does not silently replace the freeze with refresh-time recalculation.

The next integration study should compare compatible future-population and
selection assumptions through the existing Forecast/Value owners, including legal
veteran selection, incoming-player/pick conversion and no duplicate rights. It must
show effects on incumbent values, uncertainty, raw scoring and cached annual slot
priors before proposing any production behavior change. Preserve the accepted
Shapley mathematics and Career model-family/uncertainty contracts. A frozen pick
prior may be an explicitly bounded estimate; it must not be represented as an
exact joint allocation without evidence. Economic compatibility is a research gate,
not authorization to rewrite the model or change player outputs now.

Raw source files, model coefficients, selected-player outcomes and research runners
remain private. Public code is research-only with synthetic chronological and
population-accounting tests. No deployment, production data or formula was changed.
