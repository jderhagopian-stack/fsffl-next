# Native pick empirical validation — 2026-11-14

The season-stable release mechanism is implemented, but the empirical pick model
is not ready for production. This study expands usable outcome evidence and tests
a transparent comparator; it does not select reference anchors or change values.

## What was executed

Nine archived rookie rank boards (2014–2022) supplied 315 of a possible 324 top-36
rows. A pinned canonical identity map resolved 307 rows, including explicit
research-only same-class disambiguation where names collided. No fuzzy identity
match, rank compression, silent removal of veterans or zero-filled season was
used. Contemporary and retrospective positions can differ; unique canonical names
are retained independently of position, while ambiguous names remain explicit.

The previous corrected replay used **two starting WRs**, with selected base-season
cohorts (2003/2006/2009/2012/2015). Recovering their annual observations does not
recover all later-entering rookies. The recent extension used **three starting
WRs**. Those coordinates cannot be combined as if they were the same game.

The missing-label requirement was established before computing. Only 2014–2022
annual games for the existing 12-team, three-WR Superflex and 1-QB research cases
were computed: 18 games, unchanged 2,048-permutation Shapley engine and deterministic
seed. The recent 2023–2025 three-WR labels were reused after exact rules matching.
Runtime was **65.34 seconds**, peak RSS **60,284 KiB (58.9 MiB)** on the local
research process. This is neither a Render refresh benchmark nor a production
Forecast calculation. Historical supplied fantasy points remain a fixed scoring
coordinate, not proof of compatibility with arbitrary current league scoring.

## Coverage and chronological comparator

| Class | Source rows / 36 | Canonical identities | Fully observed first 3 seasons |
|---|---:|---:|---:|
| 2014 | 36 | 36 | 28 |
| 2015 | 34 | 34 | 26 |
| 2016 | 36 | 35 | 23 |
| 2017 | 36 | 35 | 28 |
| 2018 | 36 | 35 | 29 |
| 2019 | 36 | 35 | 25 |
| 2020 | 33 | 33 | 29 |
| 2021 | 32 | 30 | 26 |
| 2022 | 36 | 34 | 31 |
| Total | 315 | 307 | 245 |

Missingness and coverage are identical for both economic cases. The 245 complete
rows are **not** a representative training population: selecting only them would
change the drafted universe. No complete Career label is established; seven years
or an observed Y8+ prefix is not a career-end observation.

`scripts/evaluate_native_pick_baseline.py` tests prior-class means for the same
rank, using only classes whose entire outcome window ended before the heldout
class. A missing past slot/season or target causes an explicit abstention. This
strict comparator deliberately avoids survivor-only pooling; it is not the final
model or an archived point-in-time forecast. The three-season totals below use the
existing 0.85 discount from the **draft-season** origin. A next-year pick's current
Three-Year window instead contains only its first two post-draft seasons, shifted
one year; these benchmark errors must not be called current future-pick errors.

| Heldout | Mature training classes | Covered / 36 | SF MAE | 1-QB MAE |
|---|---|---:|---:|---:|
| 2017 | 2014 | 24 | 185.30 | 147.97 |
| 2018 | 2014–2015 | 17 | 145.17 | 111.92 |
| 2019 | 2014–2016 | 10 | 97.97 | 83.46 |
| 2020 | 2014–2017 | 11 | 107.44 | 91.39 |
| 2021 | 2014–2018 | 9 | 145.58 | 114.49 |
| 2022 | 2014–2019 | 8 | 110.14 | 91.08 |

MAE is in raw annual Shapley contribution units. Different folds cover different
subsets; falling error is not evidence of improvement. Neither a validated
selection profile nor predictive interval calibration is established by this
comparator. The same rank proxies were priced under both rule sets, so this is an
economic counterfactual, **not validated Superflex versus 1-QB drafting behavior**.

## Selection-source findings

The [FFC archive](https://fantasyfootballcalculator.com/adp/rookie/12-team/all/2014)
provides dated collection windows and mock counts. The inspected windows are
mostly late summer, not a post-NFL-draft May snapshot. Visible rank is not an
individual draft selection or an exact slot probability. QB/PPR configuration was
not independently attested for these archived rookie boards.

The [2016 board](https://fantasyfootballcalculator.com/adp/rookie/12-team/all/2016)
contains three apparent prior-year entrants. They remain in the research input;
rookie-only versus veteran-eligible selection rules need reconciliation rather
than silently dropping them. The
[2018 board](https://fantasyfootballcalculator.com/adp/rookie/12-team/all/2018)
contains an unresolved deleted identity. The
[2022 board](https://fantasyfootballcalculator.com/adp/rookie/12-team/all/2022)
includes DB and OT entries inside the top 36. These are source suitability flags,
not evidence that such selections are legal in an offense-only league.

Explicitly format-labelled expert material exists, including
[FantasyPros' 2019 SF/2QB mock](https://www.fantasypros.com/2019/05/two-round-superflex-dynasty-rookie-mock-draft-2019-fantasy-football/)
and [2021 SF expert rankings](https://www.fantasypros.com/2021/05/kyle-yates-dynasty-rookie-rankings-superflex-2021-fantasy-football/amp/).
One mock or one expert is not consensus or a distribution. Contemporary publication
date, content revision, rights, format and eligibility must be recorded before
using such material as training evidence. A current ECR embed under an old article
cannot be assumed to reproduce the old board.

## Disposition and next development

1. Retain annual economics and the exact release/reuse design. No further broad
   Shapley recomputation is needed for these 2014–2025 test coordinates.
2. Build a source-attested selection panel from actual eligible drafts/ADP and
   dated, format-specific expert inputs. Preserve individual orders or expert
   disagreement where available; a sorted consensus list alone does not determine
   selection probabilities. Validate source chronology and historical eligibility
   before adding league-specific refinement.
3. Reconcile zero-stat/participation coverage against authoritative season evidence.
   Distinguish an observed zero, a governed active-population/exit assumption and a
   missing record. Keep all selected assets and censored careers. An explicit
   model convention may be tested, but must not become a claimed observed fact.
4. Reuse the existing Forecast/Career authorities with their accepted input and
   uncertainty contracts. Foundation 4's terminal authority is a model-family
   envelope, not a validated joint annual-path distribution or Career standard
   deviation. Do not turn its midpoint or marginal bands into fabricated joint
   scenarios simply to satisfy the research bridge.
5. Compare a proposed selected-asset forecast against this comparator in frozen
   chronological class holdouts, then review actual slot estimates and mixed
   player/pick examples before production integration. Source quality, scoring
   compatibility, full-population coverage, uncertainty and live-State coordinate
   compatibility remain explicit gates. No native pick model is promoted here.

Raw boards, identities and player-level evidence stay outside the public repository.
The generic evaluator and synthetic tests are reproducible without those inputs.
