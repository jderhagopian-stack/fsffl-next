# Native pick Intrinsic research

Status: research prototype; **not eligible for production**. This work does not
change player Intrinsic, Forecast, Shapley mathematics, scoring, display scaling,
trade disposition or search ranking. Market pick prices are not native labels.

## Reuse and authority

`value/pick.py:estimate_pick_value` remains the slot-mixture owner.
`OriginPickProbabilityEvidence` remains the Value-neutral boundary for existing
Simulation slot probabilities. Owner and original franchise remain separate;
origin and draft season must match the supplied probability evidence.

The new `value/native_pick_research.py` consumes **prospective joint annual native
Shapley scenarios**, already produced upstream on an explicitly matched
rules/scoring/native coordinate. It does not fit forecasts or manufacture them
from historical actuals. Historical outcome labels must be assembled separately;
`FrozenDraftedAssetValue` is a point-in-time contract and cannot carry later
realized production under a historical draft timestamp.

Outputs use research-prefixed scales, preserve source/input fingerprints and
always report `production_eligible=false`. No production runtime route, refresh, producer or player-value reader imports
this research module. The isolated research release codec described below does
consume it; this does not enable native pick production.

## Calendar and uncertainty contract

- Three-Year is the current evaluation season plus the next two seasons, using
  the existing frozen discount. A next-year pick has two contributing seasons
  inside that window, not three rookie seasons. A pick after the window has a
  mathematically supported zero Three-Year contribution, even when Career is
  unavailable. This is distinct from filling missing data with zero.
- Career follows the accepted undiscounted annual-plus-terminal coordinate.
  Future draft delay creates pre-draft zeros, not a new blanket pick discount.
  Annual contributions and terminal remainder must not overlap. The terminal
  value must be explicit; a missing remainder is not assumed zero or retirement.
- Every positive-probability slot needs evidence for the requested horizon.
  Missing mass is never discarded or renormalized. One horizon can be usable
  for research while another remains unavailable.
- Annual and terminal values are joint scenarios. Compute each path's total
  first, then its distribution, preserving cross-year dependence. Do not add
  annual standard deviations or invent quantiles of a mixture.
- Evidence cannot postdate the evaluation cutoff. Rules, scoring, native
  coordinate and frozen engine identity must match. Signed values are retained.
  Current-season inputs must represent forward contribution from the cutoff,
  not already-earned actuals.

## Outcome-evidence audit

`scripts/audit_native_pick_evidence.py` reads explicitly supplied local historical
panel, canonical identity map, fantasy draft selections and observed native replay.
It does not download data, fit a model, recompute Shapley, or connect to production.
Its output records source hashes and distinguishes:

- observed years, including actual recorded zeros;
- missing identity or missing season/native labels;
- right-censored horizons beyond an explicitly attested complete-season boundary;
- rookie versus veteran selections, when entry identity is known.

Do not discard veteran free-agent selections when league rules allow them. Do not
substitute NFL draft position for fantasy selection order. Startup exclusions are
explicit caller configuration; they are not hardcoded league semantics. Missing
season rows cannot silently become verified zeros or complete Career observations.
Any governed zero/exit convention used by an existing forecasting model must remain
explicit and distinct from an observed source fact.

## Next empirical study, before promotion

1. Reconcile eligible selection universe, complete player identities, historical
   fantasy draft formats and the source's scoring/season completeness. Keep every
   selected asset, including low-producing, non-producing and veteran selections.
   Resolve zero-production evidence separately from missing records.
2. Use historical actuals as outcome-training/validation labels with documented
   availability cutoffs. Reuse accepted Shapley replays; extend only genuinely
   missing years and rules/scoring coordinates when necessity is established.
3. Model the prospective selected-asset distribution, including position,
   development and class uncertainty. Reuse accepted Career/survival/terminal
   machinery where its input/evidence requirements hold. Do not cap Career at the
   observed window or pretend a recent class has complete Y8+ outcomes.
4. Compare candidate forecasts with a transparent prior using chronological
   draft-class holdouts. No hindsight sorting players into historical pick slots,
   random row split across the same class, invented historical forecasts, or
   complete-case-only fit that changes the drafted universe. Report coverage,
   sample sizes, interval calibration, mean/dispersion and horizon-specific errors.
5. Produce governed native joint scenarios on supported league coordinates, then
   use this bridge and the existing slot mixture. Validate mixed packages and
   both-team accounting separately. Keep unsupported coordinates explicit.
6. Review empirical estimates and assumptions before publishing a native pick
   producer or connecting trade discovery. Existing Value/Forecast publication
   identity and bounded reuse own any eventual lifecycle; no parallel owner.

A successful contract test establishes arithmetic and evidence barriers. It does
not establish that an untrained model's pick valuations are empirically correct.

## Season-stable release policy

Exact slot economics are calculated once for an annual evaluation season, draft
year, round and supported economic/rules/scoring coordinate. When picks become
available on a league's platform, attach the applicable saved release; reuse a
shared release where eligibility and evidence rights permit. Platform availability
is an attachment event, not a reason to refit independently for every league.

Ordinary refreshes do not rebuild the curve when source timestamps, ownership,
rosters, standings or State change. The existing Market curve is already frozen;
this contract applies to the prospective native Intrinsic model as it develops.

The accepted release stages are annual baseline, post-declarations and post-NFL
draft. Later stages are explicit publication decisions supported by new evidence,
not scheduled refits implemented here. Corrections require an exact predecessor
and documented reason. Every release is content-addressed; earlier releases and
historical pick valuations remain reproducible. A subsequent annual evaluation
season requires its own release, including its own calendar-aligned Three-Year
window. Do not silently relabel a frozen research coordinate as live matching-State
player economics; that compatibility remains a promotion gate.

`value/native_pick_curve_releases.py` separates the explicit curve producer from
pure probability application. Compact distributions for every slot are retained;
annual scenario graphs are discarded from the release. Missing horizon values
remain explicit. Ownership does not affect slot economics. The originating team's
current, draft-year-specific slot probabilities can change the weighted pick value
without recomputing any slot economics. Supply probabilities governed for the
applicable round/draft-order policy; do not invent uniform distributions, infer
snake transformations, or borrow another draft year's probabilities.

`persistence/native_pick_curve.py` uses the existing store and connection owner.
An explicit producer saves a release idempotently. A reader loads an exact
reference with one bounded read; a miss or invalidation never triggers a rebuild.
There is no latest-release lookup, automatic pointer advancement, new connection
pool, global cache, worker or scheduler. The canonical publication owner must
serialize release selection and retire retained references on revocation. A warm
publication can reuse its compact frozen curve without a database read per pick.
Neither this adapter nor the research model is connected to production refresh.

## Filling selection-profile gaps

Use actual eligible fantasy draft history and format-specific rookie ADP when
available. Expert consensus **post-NFL-draft rookie fantasy rankings** can inform
an uncertain selection profile when league evidence is sparse. They describe
which assets may be selected at a slot; ranking scores are not native economic
outcome labels or a Market-to-Intrinsic conversion. Pool appropriate format-level
priors and refine them with league history rather than fitting every league in
isolation. Rankings published after the NFL draft cannot be used at an earlier
historical cutoff. Before fitting, document source availability, format fit,
coverage, uncertainty and reuse rights. No consensus source or model has been
selected or fitted in this lifecycle change.
