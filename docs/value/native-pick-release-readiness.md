# Native pick release readiness: historical context and connected scoring

Latest follow-up: [actual-draft validation](native-pick-public-draft-validation.md)
now supplies all 36 slots from 53 public Superflex drafts under explicit absence
assumptions. The earlier 24-slot mock-only result below is a historical prototype,
not the latest source-coverage limit. All 53 drafts belong to one class; predictive
validation and source/model admission remain open.

The directed-search controls can proceed through release testing independently.
Native pick valuation is still a separate production gate: the current candidate
has not established complete Career estimates or a sufficiently supported
selection distribution. A desired same-day deployment is not evidence that these
model conditions hold.

## Historical league context recovered

The existing public project
[league-history export](https://github.com/jderhagopian-stack/sleeper-league-data/blob/1179d3104cbe3330cf27e4173d61df95f2494b1a/data/league_history.json)
contains league objects, draft settings and all selections for 2022–2026.
`scripts/audit_native_pick_platform_history.py` normalizes that evidence without
fetching data, modifying records, generating forecasts or admitting a model.

The 2023–2026 records each contain 36 selections, three rounds, twelve teams,
one mandatory QB, two RBs, three WRs, one TE, one FLEX and one Superflex. The draft
eligibility code is 0 (the previously established all-player configuration),
consistent with the veterans found in the actual selections. The 2022 twenty-round
startup remains excluded. No missing selection was filled or rank compressed.

This resolves the prior absence of *exported historical* league-rule context.
It is not an immutable at-draft snapshot: the export was retrieved retrospectively
and can contain later platform amendments. Scoring also changed: fumbles lost
were -2 in the exported 2023 configuration, and -1 from 2024 onward. Current-rule
valuation of historical selections must declare that counterfactual explicitly.

## Smallest connected-scoring replay

Prior native labels were computed from the fixed supplied research points. They
cannot be relabeled as the accepted connected scoring used by Career. The
unchanged accepted `fsffl_half_ppr_points` helper is used for this new diagnostic;
no scoring formula or Shapley implementation changed.

Six Superflex annual games, 2020–2025, were identified as necessary *before*
execution. They cover the 2020 explicitly labeled Superflex source's first three
years, the actual 2023 draft's first three, and partial 2024/2025 target windows.
Two additional Superflex games, 2018 and 2019, were subsequently identified as
necessary to complete the mature-cohort first-seven-year candidate described
below. No other earlier years or 1-QB games were recomputed. The published method remains
2,048 permutations with seed 20260915.

| Year | Original player population retained |
|---|---:|
| 2020 | 618 |
| 2021 | 648 |
| 2022 | 619 |
| 2023 | 587 |
| 2024 | 597 |
| 2025 | 616 |

Primary accepted rich stats win wherever present. Sixty-six input rows absent
from that source use explicit, fingerprinted secondary stat supplements for this
research comparison. Their canonical IDs and original panel positions are
preserved. No source gaps were silently zero-filled or removed from the game.
This is a **research source-supplement hypothesis**, not a promoted production
source rule. The wider secondary-source drift audit found 13 changed rows among
6,434 common rows over 2015–2025; existing primary rows were retained rather than
replaced by the newer revisions.

The six games took 21.54 seconds, local whole-process peak RSS 58,604 KiB
(57.2 MiB). This is offline evidence, not Render latency or peak-memory proof.
The additional 2018/2019 games retained 592/587 original players and used 30
explicit secondary supplements. They took 7.55 seconds with local whole-process
peak RSS 54,816 KiB (53.5 MiB). Eight annual games were run in total.
Player publications and production data were unchanged.

## Bounded forecast diagnostic

The unmodified empirical rank prior trained on the explicit-Superflex 2020 source
was compared with actual 2023–2025 selections under the new coordinate. Missing
training seasons can only use the explicit source-corroborated absence assumption;
validation targets are always observed and never filled.

| Actual target class | Observed post-draft window | Scored / 36 | Missing observed targets | Native MAE |
|---|---:|---:|---:|---:|
| 2023 | First 3 seasons | 27 | 9 | 154.25 |
| 2024 | First 2, in next-year pick calendar | 29 | 7 | 72.53 |
| 2025 | First 1, in two-years-away calendar | 33 | 3 | 28.35 |

These are three different windows and evidence subsets, not an error trend. They
are retrospective research diagnostics, not fresh holdouts or validated
population uncertainty. The 2020 source is a single expert board, not consensus,
and its full scoring/lineup vintage remains qualified. The target league's
all-player eligibility is not identical to a rookie-only source. Errors on the
legacy and connected coordinates must not be compared as though their units were
unchanged. No model winner is promoted by these results.

## Career gate remains substantive

The accepted Career model is available; it has not been lost. Its live dynamic
adapter consumes complete governed individual-player P0 rows, exact State facts
and a fixed reference cohort. It does not supply an already-validated future draft
cohort prior. Bypassing its State/forecast checks or pretending anonymous future
entrants are current rostered players would not establish that missing input.

A check against the saved 2026-11-08 State/publication illustrates the coverage
problem. Of the 60 players in the 2020 Superflex board, 19 have published remaining
Career values, six are in canonical State without that publication, and 35 are
outside that State. Keeping only the 19 would select survivors. Treating the other
41 as retired or zero would invent evidence. The snapshot is historical, not the
latest live publication, and these counts are not a new current coverage defect.

### Mature-cohort Career candidate implemented

`scripts/fit_native_pick_mature_career_prior.py` now constructs an alternative
that avoids filtering on today's Career publication: observed first-seven-year
native contributions from mature historical classes, followed by the unchanged
accepted `build_career_tail_authority` Y8+ model. Each sample declares the last
observed season and first modeled season; no overlapping actual tail is added.
This is an empirical training outcome with model continuation, not an archived
point-in-time forecast. Model authority bands are not class dispersion or a
predictive confidence interval.

The private diagnostic uses two post-NFL-draft source profiles: the 2018
[RotoUnderworld round one](https://www.playerprofiler.com/article/rotounderworld-superflex-dynasty-league-mock-rookie-draft-round-1/)
and [round two](https://www.playerprofiler.com/article/rotounderworld-superflex-dynasty-league-mock-rookie-draft-advanced-stats-metrics-analytics-2/)
Superflex mock, and the 2019
[FantasyPros two-round 2QB/Superflex mock](https://www.fantasypros.com/2019/05/two-round-superflex-dynasty-rookie-mock-draft-2019-fantasy-football/).
These are multi-author mock examples, **not expert consensus**. All 48 identities
resolve through unique name and draft-class evidence; current NFL position is
not used to reject a historical rookie identity. Original source positions remain
explicit.

With strict observed-season requirements, 4/36 slots have complete class support.
Under the separately recorded source-corroborated absence assumption, 24/36 do;
61 absent player-seasons remain declared assumptions, not certified actual zeros.
The last 12 slots lack source profiles. The two-class sample, full-PPR versus
half-PPR source differences, and rookie-only versus all-player draft eligibility
still require validation. Accepted tail capacity is the supported 12-team,
three-WR Superflex configuration; this does not establish a 1-QB tail.

A model-assisted historical Career reference must retain the complete selected
cohort, keep observed prefixes separate from model continuation, and prove their
calendar/scoring compatibility and non-overlap. Reference-comparison policy may
be reused where supported; this does not require repricing current players. The
remaining work is that cohort input/continuation validation and adequate selection
coverage, followed by actual matching-State legal-package replay. A partial
observed sum, an arbitrary multiplier or Market values cannot substitute for it.

## Release disposition

Do not deploy unvalidated pick Intrinsic as part of the requested update. The
search-controls PR #553 has passed its exact-head full-suite gate; it remains
unmerged and undeployed pending the requested valuation-dependent release. No user permission question is needed for the remaining authorized
research. If the valuation evidence is not complete in time, report that limitation
and keep the release gate open rather than claim the model is resolved.
