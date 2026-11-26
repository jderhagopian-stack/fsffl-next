# Native pick model sensitivity and later-class check — 2026-11-14

A rank-smoothed historical prior improved exploratory errors but did **not** show a
materially consistent improvement on the later actual-league draft check. No pick
model, missing-season assumption or native value is promoted by this study.

## What changed in the research implementation

The chronological evaluator now supports two declared candidates:

- `slot_mean`: mean of earlier mature-class outcomes at the same rank;
- `isotonic_slot_mean`: the same complete training-slot means, smoothed by
  pool-adjacent-violators regression so expected contribution weakly decreases
  with draft rank.

The smoothing relation is a research hypothesis about selection order, not a
change to player economics or an attempt to match dynasty prices. It uses no
Market values, manual anchors or tuning weights. Training slots have equal class
counts; missing/unsupported slots are never interpolated into available values.
The fit uses all eligible training slots before looking at validation outcomes.
It does not fit only the subset whose target outcomes happen to be observed.

`scripts/evaluate_pick_missingness_sensitivity.py` adds an explicit, read-only
scenario: for a known canonical player and mature **training** season, absence
from the supplied statistical panel is assumed to mean no fantasy production.
This scenario requires an assumption reference and exact source-panel digest.
It cannot fill a missing native replay value when the source player-season exists,
resolve a missing identity, fill a missing selection, infer career termination,
fill a future/censored label, or impute a validation target. The input is unchanged
and every assumption use is recorded. Default strict evaluation remains intact.

This is a population-completeness assumption, **not a verified historical fact**.
Inspection of the richer historical source found no zero-games rows and did not
establish every absent player's participation or zero statistics. The richer
source and supplied panel have different row sets; one must not be used to attest
the other's completeness. Before production use, reconcile their source windows,
player populations, scoring inputs and explicit zero/exit conventions. Current
unsigned/IR/no-ROS exceptions do not establish past annual zero facts.

## Exploratory comparisons

The 2017–2022 chronological folds use the same fixed supplied historical points,
12-team/three-WR SF and 1-QB economic cases, and frozen annual Shapley labels as the
[earlier study](native-pick-empirical-validation.md). No annual game was rerun.
Historical selection-format equivalence is still unverified, so these remain
counterfactual economics on the same rank proxies, not calibrated drafting behavior.

| Heldout class | Strict scored / 36 | Training-assumption scenario scored / 36 |
|---|---:|---:|
| 2017 | 24 | 28 |
| 2018 | 17 | 28 |
| 2019 | 10 | 23 |
| 2020 | 11 | 27 |
| 2021 | 9 | 24 |
| 2022 | 8 | 26 |

Every scored target remains observed. The scenario expands training coverage;
it does not create validation truth. Its target coverage is still selective.

Across the same 156 scored observations per economic case in the expanded
scenario, descriptive pooled MAE was:

| Economic case | Independent rank means | Smoothed rank prior | Reduction |
|---|---:|---:|---:|
| Superflex | 124.25 | 107.39 | 13.6% |
| 1-QB | 103.16 | 88.08 | 14.6% |

These are exploratory comparisons on correlated class samples, not significance
tests, validated intervals or proof of production superiority. Candidate design
followed inspection of the earlier baseline evidence; those classes are not an
untouched confirmation set. Comparing strict and expanded errors without matching
target coverage would confound coverage with forecast quality. The script also
reports errors on common observed targets for that reason.

## Candidate freeze and actual 2023 draft check

Candidate code was published at `8ae7c38eee96c2e20811f1658e93828ce549744b` before
constructing/running the later-class comparison. A retained protocol fixes both
candidates, 2014–2020 mature training classes, 36 ranks, first-three-season horizon,
0.85 discount, source boundary 2025 and observed-only targets. Code digests are
checked by the private runner. No candidate pruning or tuning followed the result.
The 2023 class had appeared in prior source/coverage and first-year research;
this is a later-class candidate check, not a claim the entire class was never seen
or that these are archived historical forecasts.

The target is the supplied **actual 2023 league draft**, including veteran
selections, rather than a heldout ADP list. Of 36 picks, 27 have complete observed
three-season labels; 24 also have supported training ranks under the assumption
scenario. Strict training permits only seven. The training scenario uses 76
explicit training-entry/season zero assumptions. Validation targets are untouched.

| Economic case | Covered | Rank-mean MAE | Smoothed-prior MAE | Result |
|---|---:|---:|---:|---|
| Superflex | 24 / 36 | 102.28 | 101.83 | 0.4% lower error |
| 1-QB counterfactual | 24 / 36 | 90.05 | 90.77 | 0.8% higher error |

These are draft-season first-three-season discounted raw Shapley units. They are
not the current Three-Year value of a next-year pick. Future pick calendar
alignment continues to be owned by the existing research horizon bridge.
The check took 0.22 seconds and 20,828 KiB peak RSS locally, reusing saved annual
labels. It is not a Render or production-refresh measurement.

The earlier apparent gain does not establish a robust improvement. Retain both
candidates as comparators; do not promote the smoother, select anchors, or tune
against named players to make this check look better. No full Career label,
Career variance or predictive interval is established here.

## Better format evidence acquired

A [published 2021 actual-draft report](https://www.fftoday.com/articles/billanderson/21_rookie_draft.html)
provides 1-QB and Superflex drafts, explicit lineups, 0.5-PPR scoring and dates.
We retained 47 reported selections with canonical identities: 23 in 1-QB and 24 in
SF. The omitted 1-QB 2.09 remains missing; later ranks are not shifted. Twelve
teams are inferred from twelve selections per reported round, not independently
attested league metadata. Veteran eligibility is not supplied. The first rounds
contain three and four QBs respectively, descriptive facts from two drafts only.
The reported SF lineup has no additional ordinary FLEX; it is not identical to
our SF economic test case, which includes both FLEX and SUPERFLEX.

These retrospectively retrieved reports are more explicit about format than the
archived rank proxies, but are not preserved 2021 provider snapshots or a
representative selection distribution. Do not treat two drafts as consensus.
A [2020 FantasyPros consensus article](https://www.fantasypros.com/2020/05/fantasypros-2020-staff-consensus-dynasty-rookie-rankings-fantasy-football/)
explicitly identifies PPR/1-QB and three experts; its ranking rows are in an embed
that did not yield a recoverable table. No rows or disagreements were invented.
Raw reports, identities, research protocol and model outputs remain private.

## Development disposition

The annual frozen slot-release design is unchanged. The next forecast must model
what assets a slot can select and their football outcomes, with format-specific
selection evidence and explicit uncertainty. Rank alone can remain a comparator,
but does not supply class strength, positional mix, veteran eligibility or an
owner's departures from consensus. Do not manufacture selection probabilities
from one sorted list or assume rankings from one format apply unchanged to another.

Use the newly explicit draft evidence as part of a larger selection panel. Reuse
accepted Forecast/Career authorities on compatible inputs; broad entry-level
outcome evidence can inform cohorts that recent fantasy drafts cannot mature.
Preserve Foundation4's model-family envelope and unvalidated cross-horizon
covariance rather than fabricating joint paths or scalar certainty. Freeze a
feature-informed candidate and fresh validation plan before its next economic
review. Do not repeatedly tune on the 2023 result or promote the missing-season
assumption as an observed fact. No production integration is justified yet.
