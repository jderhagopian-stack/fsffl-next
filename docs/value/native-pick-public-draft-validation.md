# Native pick prior: actual-draft selection evidence

Status: research only. The third-round selection-coverage gap is resolved for this
sample. Predictive validity and production admission are not established.

## Source and scope

The public [DynastyProcess MFL dataset](https://github.com/dynastyprocess/data-mfl_public)
contains draft selections and league summaries under CC0. The pinned source is
commit `9b8f37152036b44b1a5baeb35f70482b1d3369f8`, dated 2021-07-31. Its 2019
SafeLeagues partitions contain 349 league summaries and 69,672 selections, covering
both startup and supplemental drafts. They are not interchangeable observations.

`scripts/audit_native_pick_public_drafts.py` consumes normalized records. It
requires twelve teams, one player copy, ordinary full PPR, no IDP, best ball,
salary cap or TE premium, explicit QB capacity, complete four-round coordinates,
unique selected identities and a declared post-NFL-draft time window. Startup,
incomplete and placeholder-containing drafts are excluded as entire records
before looking at economic outcomes. No pick is shifted or rank-compressed.
Exclusions remain in the audit. Four-round structure identifies a supplemental
*candidate*; it does not certify a league's full eligibility policy.

The resulting sample contains **53 Superflex and 48 separate 1-QB drafts**;
248 league records are excluded. Accepted selections occurred May 6–15, 2019.
The Superflex records explicitly allow one to two quarterbacks; the 1-QB records
allow one. Broader starting-lineup details are unavailable in the summary.
The first 36 slots of each accepted draft are retained, including the third round.
All 60 distinct selected Superflex players resolve through a unique source-ID to
canonical-ID crosswalk and have a 2019 draft year. No unresolved identities remain
in that sample. This is observed selection evidence, not consensus rankings or
market-price evidence.

The full-PPR source is not an exact half-PPR choice distribution. The first three
rounds of four-round drafts need not match three-round drafts perfectly. One
provider and overlapping managers can create correlated choices. These
qualifications survive the research projection.

## Career candidate and annual freeze

The existing mature candidate uses observed Y1–Y7 native contributions plus the
unchanged accepted Y8+ model authority. The observed prefix ends in 2025 for this
2019 class; the terminal starts in 2026. No overlapping actual tail is added.
Original connected-scoring annual games are reused; **no additional Shapley games
were run** for this follow-up. No player formulas, scoring, source rules or display
anchors changed.

Every source draft is fitted separately. The summary helper
`scripts/summarize_native_pick_mature_prior.py` averages observed draft frequencies
within one explicit class, rejects mixed economic/class coordinates, and withholds
a slot if any requested source draft lacks authority. It does not silently drop
missing outcomes or turn many leagues into many independent draft classes.

With strict observed-season requirements, no slot has support from *every* one
of the 53 drafts. Under the separately fingerprinted source-corroborated absence
assumption, **all 36 slots do**. There are 173 distinct assumed player-seasons
across the selected sample. Source absence remains an assumption, not certified
actual zero; repeated appearances do not create new absence evidence.

Three Career reference curves, one per round, were frozen and round-tripped
through the existing persistence codec using an in-memory test store. Saving each
twice produced three writes, not six. All 36 slots retained their model-authority
envelopes and `production_eligible=false`. The measured local freeze/restore was
0.038 seconds; whole-process RSS was 222,820 KiB, including imports. This is not
incremental hosted memory. No production database or current-State attachment was
used. PyArrow was used only in a private offline extraction environment; it is not
a new application dependency.

Career bands remain model-authority bounds, not predictive confidence intervals,
class dispersion or a standard deviation. The accepted terminal's supported
capacity is the existing twelve-team, three-WR Superflex configuration. Finding
1-QB selection records does not validate or authorize a 1-QB Career tail.

## Chronological three-year diagnostic

For a hypothetical 2022 release of a 2023 pick, the literal current-three-year
calendar includes only its first two post-draft seasons, discounted by 0.85 and
0.85 squared. Training uses the 2019 cohort; its first three seasons end in 2021,
before the hypothetical release. The draft export predates that release too.
This is a retrospectively constructed model diagnostic, **not an archived
point-in-time forecast or a fresh holdout**. Corrected historical actuals remain
outcome evidence, not historical forecasts.

Actual 2023 league selections provide 32/36 observed two-season targets. Four
missing targets remain missing and are never filled.

| Training treatment | Targets scored | Observed targets lacking training support | Native MAE |
|---|---:|---:|---:|
| Strict | 9/36 | 23 | 64.95 |
| Explicit corroborated-absence assumption | 32/36 | 0 | 58.14 |

The rows score different subsets. They do not establish an accuracy improvement.
The earlier 2020-board diagnostic used a different 2023 calendar window and is not
a same-unit/window error comparator. No winner or calibrated uncertainty follows.

## Findings and remaining release gate

- Third-round source coverage is no longer the blocker for this Superflex sample.
- The data describe **one independent class**, despite 53 drafts. Career fitting
  can still overreact to that class's particular successes and failures.
- The unsmoothed Career curve rises at 14 adjacent slot transitions. This is
  evidence of a noisy class/selection outcome estimator, not proof that later
  selection rights are economically superior. No monotonic correction is applied.
- Additional independent-class evidence, continuation transport and missingness
  validation remain necessary before presenting these as reliable current values.
- Real matching-State trade acceptance must use actual publication, inventory,
  probability and source-time evidence. Newly fitted curves cannot be backdated
  to make an older saved State pass the attachment guards.

The architecture can preserve the requested annual freeze and reuse current
ownership/slot probabilities cheaply. The remaining work is model evidence and
admission, followed by targeted legal-package replay, not a new refresh-time fitter
or replacement valuation architecture. No implementation is merged or deployed.
