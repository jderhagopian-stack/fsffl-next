# Native pick cohort prior: fitted research candidate

No user decision or additional permission is needed for this work. The accepted
path is to estimate native football contribution from historically selected assets,
use format-specific post-NFL-draft expert consensus/ADP for selection gaps, validate
chronologically and freeze the admitted annual slot curve. Rankings identify
selection opportunities; they never become native prices. Market remains a
separate feasibility channel.

## What was fitted

`scripts/fit_native_pick_cohort_prior.py` now fits an empirical three-season joint
trajectory prior from mature historical class-slot observations. Each available
class receives its empirical frequency, preserving its annual path rather than
independently sampling years or summing standard deviations. Every requested
mature class must be supported at a slot; incomplete classes are not discarded.
Existing scoring coordinates, native annual Shapley labels, calendar discounts
and the annual curve consumer remain unchanged. The fitted scenario dispersion
is uncalibrated, not a confidence interval or validated predictive distribution.

The current exercise uses ten classes, 2014–2023, for an explicitly dated 2026
research bootstrap and 2027 picks. This is not a backdated release or an archived
forecast. The retained selection panel has mixed rank proxies and an actual 2023
draft, with format/vintage limitations. It is not admitted as the production
Superflex or 1-QB selection distribution.

| Scenario | Round 1 supported slots | Round 2 | Round 3 |
|---|---:|---:|---:|
| Strict observed labels | 5 / 12 | 1 / 12 | 0 / 12 |
| Explicit source-corroborated absence sensitivity | 11 / 12 | 10 / 12 | 5 / 12 |

The sensitivity's missing native seasons are **assumed zero for research**, with
fingerprinted corroborating evidence and an explicit assumption reference. They
are not relabeled observed zeros. There are 61 such assumed seasons in the 26
supported slots; assumptions at unsupported slots are not retained as fitted
training observations. Selection-rank and identity gaps still withhold ten slots.

The actual fitted scenarios passed through the existing annual freezer: twelve
local curves, covering two economic cases, three rounds and two evidence
scenarios. All Career fields remain unavailable. This verifies fit-to-freeze
integration, not production admission. The research freezer's unused attachment
fields were explicitly synthetic; no real owner, draft probability, State or trade
recommendation is claimed. Freezing took 0.028 seconds locally, whole-process
42,636 KiB including imports. No source/model fitting happens during refresh.

## Missing-season reconciliation

A new independent source check uses regular-season player summaries from
[nflverse-data](https://github.com/nflverse/nflverse-data/releases/tag/player_stats)
for 2015–2024 and the
[current stats-player source](https://github.com/nflverse/nflverse-data/releases/tag/stats_player)
for 2025, following the
[official loader](https://github.com/nflverse/nflreadr/blob/main/R/load_stats.R).
Private snapshots retain exact bytes, URLs and SHA256s. They are retrieved source
vintages, not reconstructed historical snapshots.

All **103 distinct missing player-seasons** are absent from those broader tables.
As a positive control, **all 6,596 existing native-panel player-season keys** in
those eleven years appear in the new source. The check also retains one unresolved
source identity row per year; it does not silently discard that qualification.
The result supports a source-absence sensitivity but does not independently
certify that no scoring event occurred for an absent identity.

`scripts/reconcile_native_pick_season_evidence.py` validates fingerprints,
regular-season/calendar scope, duplicate keys and unresolved source identities.
A present stats row without a native label remains unresolved; source absence
never directly fills a native label. The fitted-prior script only uses absence
as an explicit, optional training assumption. Validation targets are never filled.
The bounded reconciliation took 0.335 seconds and 34,872 KiB peak RSS locally.

## Chronological evidence

A retrospective diagnostic evaluates next-year picks in a literal current
three-season calendar window: only the first two post-draft seasons contribute,
with the accepted year-two and year-three discounts. For drafts 2018–2023,
training windows must finish before the preceding annual release year. No target
class or immature training label enters its own fit.

| Scenario | Scored / 216 class-slot targets | SF MAE | 1-QB economic-counterfactual MAE |
|---|---:|---:|---:|
| Strict | 88 | 88.04 | 71.65 |
| Corroborated-absence sensitivity | 173 | 72.71 | 61.12 |

There are 32 missing observed targets in both scenarios. Unsupported priors among
observed targets fall from 96 to 11. The scored subsets differ; the lower aggregate
MAE is **not proof of greater predictive accuracy**. Supported strict slots retain
the same fit in the sensitivity. The additional coverage is the measured result.
These cohorts/targets have already appeared in research, and source vintage and
selection-format qualifications remain. This is neither a fresh holdout nor
population-level interval calibration, nor validation against actual 1-QB drafts.
No new annual Shapley games were needed.

## Career continuation: exact reuse requirements

`value/career_forward_intrinsic.py:build_career_forward_intrinsic_shadow` requires
ready raw Y1–Y3 contributions, ready Y4–Y7 authorities and a terminal authority
for the identical player cohort and evaluation season. Finite historical sums
cannot be placed into that contract as full Career evidence.

`value/career_tail.py:build_career_tail_authority` requires age, experience,
current and prior production features in the governed connected-league scoring
coordinate. Its current terminal package supports the accepted twelve-team,
three-WR Superflex capacity signature. A synthetic contract probe succeeds for
that signature and scoring, but rejects fixed supplied-panel scoring and the
representative 1-QB signature. Successful contract acceptance does not establish
rookie-cohort predictive validity.

Consequently the accepted terminal coefficients cannot simply be applied to the
current fixed-panel native labels or copied to 1-QB. Continue through the existing
Forecast/Value owners with supported scoring, population and feature transport.
Keep observed prefixes and model-completed continuation separately labeled and
non-overlapping; never label a current model as a historical point-in-time forecast.
Named-prospect forecasting remains later work, not a prerequisite for a historical
cohort prior. No new tail, replacement valuation or player repricing is introduced.

## Remaining production gates

The candidate now produces real fitted Three-Year estimates and immutable research
curves. It remains production-ineligible until the selection profile is supported
for the intended league and validation disposes of the missingness/uncertainty
assumptions. Career also needs a correctly governed cohort continuation through
existing model owners. Then replay saved matching-State legal player/pick packages,
including cuts and both teams' objectives, before connecting discovery.

Validation: 199 focused tests passed in 4.20 seconds, including source
reconciliation, empirical fitting, fit-to-freeze, prior contracts and the existing
pick/Career/trade regression set. Production code/formulas, model packages,
calibration anchors and deployment remain unchanged.
