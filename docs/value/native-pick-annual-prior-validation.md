# Annual native pick prior: evidence coverage and selection-source validation

The annual freeze remains the right lifecycle design. The next bottleneck is the
selection/outcome evidence used to populate that release, not refresh speed or a
need to change player Intrinsic. This continuation adds an executable annual
cohort audit and improves the historical source panel. It does not promote a pick
model or change production.

## Annual cohort audit

`scripts/audit_native_pick_annual_prior.py` reuses existing annual native outputs,
source coordinates and numerical validators. For a 2026 research release it uses
2014–2023 classes with complete calendar windows ending by 2025. It retains every
requested class at each slot; missing identities, selections and season labels
prevent that slot's complete-label mean instead of silently excluding failures.
Source/retrieval vintage and format qualifications remain visible. This is a
retrospective diagnostic, not an archived 2026 production forecast.

| Evidence available across all ten classes | Supported / requested slots |
|---|---:|
| First three post-draft seasons | 6 / 36 |
| First two seasons, discounted into a next-year pick's current 3-Year window | 15 / 36 |
| First season, discounted into a two-years-away pick's current 3-Year window | 19 / 36 |

The two economic cases, 12-team three-WR Superflex and 1-QB, have identical source
coverage but separate native outcomes. Across each case's 360 requested class-slot
cells, there are 71 player-class rows missing at least one native season label,
eight unresolved identities and nine absent selection ranks. The 71 rows contain
103 missing player-seasons absent from the supplied panel; they are not verified
zeros. No missing replay-with-panel-present season was identified in those gaps.
Some unresolved rows are non-offensive or deleted source entries; do not invent
player identities, backfill unrelated ranks or treat those rows as zeros.

The audit reports leave-one-class mean ranges where every required label exists.
Those ranges measure sensitivity to training-class choice, not confidence
intervals, predictive uncertainty or full Career economics. Offsets use the same
mature class set, preserve current calendar discounting, and can use an observed
prefix without imputing missing later years. No finite observed window becomes a
Career label, retirement assertion or Y8+ terminal estimate.

The strict diagnostic is a coverage test, not a claim that partial data makes all
bounded estimation impossible. A model that explicitly handles censoring and
selection uncertainty can use more evidence, but needs its own validation.

## Additional source evidence

Three additional published boards supply 140 ranking entries, all mapped to a
unique canonical identity using normalized name/merge-name and draft class:

- [Sharp Football 2020 Superflex post-draft top 60](https://www.sharpfootballanalysis.com/fantasy/2020-fantasy-football-rankings-post-draft-rookie-superflex-top-60/):
  60 entries; explicitly Superflex; 41 complete observed first-three labels.
- [Sharp Football 2020 ordinary post-draft top 60](https://www.sharpfootballanalysis.com/fantasy/2020-fantasy-football-rankings-post-draft-rookie-top-60/):
  60 entries; ordinary overall board, one-QB interpretation remains an inference;
  42 complete observed first-three labels. Same author as the Superflex board,
  not an independent expert consensus.
- [FantasyPros 2022 staff-consensus Superflex/2QB board](https://www.fantasypros.com/2022/08/dynasty-rookie-superflex-fantasy-football-draft-rankings-fantasypros-staff-consensus-2022/):
  20 entries; explicitly combined Superflex/2QB; 19 complete observed labels.

These are ranking entries, not 140 distinct players or actual draft selections.
They improve format evidence but do not attest complete lineup/scoring/team-count
rules. Rookie-only lists do not describe all options in a veteran-eligible draft.
The retrieved pages have later modifications; historical publication paths and
post-draft wording do not establish that every row was preserved unchanged at the
original timestamp. Store retrieval evidence and qualify vintage explicitly.

Several additional leads remain unusable: a historical FantasyPros ADP page
currently reports zero sources, a 2021 Sharp rankings page lacks its table in the
retrieved body, and DLF sources could not be consistently retrieved. No data is
invented from those leads. The 2022 May FantasyPros article retains pre-draft
introductory wording alongside post-draft teams; its vintage is ambiguous and it
was not selected over the explicitly labeled August board.

## Source sensitivity, not a new model winner

The two same-author 2020 boards give a useful controlled selection-source check.
Their first twelve contain three QBs versus zero. Both were passed separately
through the existing unmodified rank-mean evaluator, using only 2020 training
labels matured before 2023 and the already examined actual 2023 league draft as
target. Neither missing training nor target seasons was zero-filled. Each board
covers 23 of 36 targets; 19 targets are common to both.

| Native economic case | Explicit-Superflex board MAE, common 19 | Ordinary-board MAE, common 19 |
|---|---:|---:|
| Superflex | 116.09 | 217.29 |
| 1-QB counterfactual | 125.59 | 199.03 |

These numbers demonstrate sensitivity to the selection profile. They do not
validate a production estimator or establish superiority over the previous
multi-class candidate. This is one training class and a reused target, with an
exploratory comparison rather than a preregistered fresh holdout. Both rows use
the same actual Superflex league's selections; the 1-QB row changes the economics,
not the drafting behavior. It is therefore not validation against actual 1-QB
drafts. Exact scoring and source-vintage mismatches remain unresolved.

No new annual Shapley games, historical forecasts or Career tails were computed.
Raw source tables, identities, fitted estimates and target-level results remain
in private research evidence; this report publishes only aggregate diagnostics.

## Next implementation work

1. Expand the normalized, format-specific selection panel using independently
   dated post-NFL-draft consensus/ADP sources. Preserve source diversity and missing
   rows; separate actual selections from ordinal expert opinions. Do not turn
   ordinal rankings into native prices or use arbitrarily equal source weights.
2. Reconcile the 103 absent player-seasons against an exhaustive, accepted
   participation/stat population or explicit source-coverage evidence. Until
   then, zeros remain a sensitivity assumption rather than observed training truth.
3. Use the accepted Career continuation authority for a cohort prior with explicit
   censoring and uncertainty, preserving terminal scope. Named-prospect forecasts
   remain a later capability; waiting for current rookies to finish their careers
   is not required. No new survival model or tail is selected in this audit.
4. With an admitted annual prior and source context, run the existing isolated
   player/pick binding on saved matching-State packages. Evaluate both teams with
   existing Decision objectives and roster cuts before connecting discovery.

There is no user preference or approval decision blocking these research actions.
The missing inputs are technical evidence tasks, not reasons to ask Management to
approve fabricated labels or a premature production rollout.

Validation: 186 focused tests passed in 4.40 seconds, including nine annual-audit
contracts and the prior pick/Career/trade regression set. The bounded annual audit
took 0.026 seconds with 12,380 KiB whole-process peak RSS locally. No hosted,
full-suite, real-league pick-model accuracy or deployment claim is made.
