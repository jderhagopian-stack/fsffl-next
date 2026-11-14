# Multi-class native pick candidate

## Result

The public actual-draft sample now spans 222 qualifying Superflex drafts:
53 from 2019, 75 from 2020 and 94 from 2021. All 36 first-three-round
coordinates remain explicit. These are three classes, not 222 independent
class-strength observations. The candidate remains research-only.

The added files come from the same CC0
[public MFL archive](https://github.com/dynastyprocess/data-mfl_public/tree/9b8f37152036b44b1a5baeb35f70482b1d3369f8).
Existing qualification checks require complete post-NFL-draft selections,
12 teams, single-copy rosters, full PPR, explicit QB/Superflex requirements,
and no identified IDP, TE premium, best ball or salary-cap variants. Three
2020 draft groups without league metadata were quarantined; missing timestamps
remain exclusion evidence. Separate qualifying 1-QB drafts were not pooled into
Superflex selection probabilities. The full-PPR choice evidence is being
transported to the declared connected scoring coordinate; it is not evidence
that the formats have identical selection preferences.

## Candidate construction

`scripts/fit_native_pick_empirical_prefix.py` supplies one class-balanced
empirical first-three-year trajectory prior from the actual 2019–2021 drafts.
Each class receives equal weight, then each draft within its class receives
equal weight. Historical selections are not presented as point-in-time
forecasts. Training absence assumptions remain attributed assumptions, while
unresolved identities remain missing.

`scripts/fit_native_pick_selection_transport.py` supplies a separate research
long-term component. Actual Superflex selection frequencies determine the
mixture of position and within-position selection priority at each overall
slot. Mature 2014, 2016, 2017, 2018 and 2019 outcome classes supply conditional
first-seven-year native outcomes and the unchanged accepted Y8+ continuation.
The incomplete 2015 first-36 source is excluded for source coverage, not its
outcomes. The older sources' overall ranks are never relabeled Superflex ranks;
within-position transport remains an explicit modeling hypothesis. Mock sources
are not consensus rankings.

Missing component probability mass uses an identified same-slot 2019 empirical
forecast backoff, or the slot is withheld. It is never renormalized away or
converted into a fabricated historical zero. Mean backoff mass is approximately
0.059% for the actual-draft prefix and 12.39% for the long-term transport.

`compose_reference` shares the empirical first-three-year authority across
3-Year and Career. Career removes the transport model's first-three-year
reference and appends the canonical empirical prefix exactly once. There is no
chosen blend coefficient or second competing prefix. The existing calendar,
0.85 discount for 3-Year, undiscounted Career and terminal model remain intact.
Career authority envelopes remain model references, not predictive intervals.

Four additional connected-scoring annual games, 2014–2017, were identified
before execution as necessary to complete the mature source windows. They
retained the original populations of 568, 578, 579 and 575 players and used
90 explicitly fingerprinted secondary supplements only where primary evidence
was absent. Unchanged scoring and Shapley code used 2,048 permutations and seed
20260915. These four games took 13.98 seconds with local whole-process peak RSS
58,008 KiB. Together with the earlier eight games, twelve annual games have now
been run. This is offline research evidence, not hosted resource acceptance or
promotion of a new production source rule.

## Observed-target diagnostics

Validation targets are never zero-filled. All errors below are in the same
declared connected native coordinate. The comparator is the existing single-class
2019 empirical prior, not market price. The chronological 2023 checks use only
source classes whose required observed prefix ended before the declared release
season. Reconstructed historical inputs are not archived forecasts or fresh
holdouts.

| Target and window | Scored coverage | Candidate MAE | 2019 baseline MAE |
|---|---:|---:|---:|
| 2023, first two seasons in next-year 3-Year calendar | 32 / 36 slots | 58.98 | 58.14 |
| 2023, first three seasons | 27 / 36 slots | 109.26 | 105.23 |
| 2020, first-five-year observed rank means | 36 rank means | 143.98 | 165.80 |
| 2021, first-five-year observed rank means | 36 rank means | 116.44 | 138.64 |

The 2020 and 2021 diagnostics exclude the target selection class from both the
prefix and selection-mixture fit. They are current-model cross-class checks,
not historical point-in-time forecasts. Rank means use only fully observed
player windows, with varying draft counts and selective coverage; 36 rank means
does not mean every selected player's five seasons are observed. Neither check
validates the complete Career tail. The candidate improves these longer-prefix
comparisons but slightly worsens both 2023 checks. No validated superiority or
complete Career accuracy is claimed.

## Research replay clock

The isolated research binding now distinguishes football State time from model
evaluation time. The default remains strict point-in-time mode. An explicit
`current_model_replay` can apply a newly released research model to an older,
unchanged exact State without backdating the model or calling it an archived
forecast. Player publication identity, State, generation, inventory, origin,
round and probability evidence cutoffs remain enforced. New model availability
does not permit later football facts to enter an earlier State. Runtime imports
and production eligibility remain unchanged.

## Production disposition

The charter permits a bounded, documented provisional prior; perfect historical
forecasts are not a prerequisite. This candidate is a stronger-supported
research proposal than a single-class source. Nevertheless, source-format
transport, assumed inactive seasons, slot reversals, and long-term generalization
remain qualifications to assess before admitting it as pick Value authority.
A raw native package balance is not franchise utility, owner willingness or a
mutually beneficial recommendation. No production model, formula, calibration,
reference anchor, source rule or deployment is changed by this report.
