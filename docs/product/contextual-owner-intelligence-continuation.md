# Contextual owner intelligence: continuation of the accepted direction

## What the roadmap means

[PRODUCT_ROADMAP](../operations/PRODUCT_ROADMAP.md), especially “Legacy FSFFL
capability harvest” item8 and Phase3, calls for roster-need and opportunity
normalization, other-owner priors and shrinkage. The
[strategic discovery contract](../opportunity/strategic-trade-discovery.md)
distinguishes durable tendencies, current circumstances and explicit search
instructions. The objective is understanding past choices in their context so
supported tendencies can inform future opportunities, not listing acquisitions.

A contender who sold receivers while deep at WR has not demonstrated a general
preference for selling receivers or rebuilding. A useful interpretation asks
what need or surplus existed then, what the owner received, which alternatives
were evidenced, and whether similar choices recur beyond that context. Applying
that tendency today additionally requires current team circumstances. This
example defines the question; it is not an asserted fact about any real owner.

## Original implementation inspected, not adopted

Pinned predecessor `jderhagopian-stack/sleeper-league-data` commit
`1179d3104cbe3330cf27e4173d61df95f2494b1a`:

- `script/build_behavioral_action_context.py`: consumes shared historical roster
  reconstruction and prior-completed-season player quality; separates unknown
  quality. It also embeds fixed position inventory/quality targets and fixed
  rank cutoffs. Preserve the information categories, not those league constants.
- `script/behavioral_intelligence_v3.py`: expected acquisition mix combines roster
  need and other-owner action-type acquisition priors; residuals shrink toward
  neutral. Its opportunity proxy is what other owners acquired, not a verified
  list of every available offer. Its pooled environment is built from the input
  action collection; a predictive backtest must explicitly exclude later actions.
- `script/historical_state_behavior.py` and
  `script/trade_decision/historical_behavior_policy.py`: use prior results and
  approximate roster-age context, then prefer history from comparable competitive
  situations. Fixed blend/fit coefficients and approximate states are not NEXT
  authorities or calibrated acceptance probabilities.
- `script/behavioral_intelligence_v3_production.py` explicitly declares
  `NOT_PREDICTIVELY_VALIDATED`; software promotion did not prove future behavior.
- `script/trade_behavioral_intelligence.py` consumes normalized positions alongside
  pick/package/youth traits. Feature breadth is not empirical validation.

No legacy data payloads or models were executed or imported into production.

## NEXT components to reuse

`behavioral/action_context.py`, `trade_context_dataset.py`,
`context_expectation_v2.py`, `historical_context_profile.py`,
`residual_preference.py`, `context_controlled_profile.py` and
`trade_decision/behavioral_contextual_value.py` already provide pre-action context,
strictly-earlier other-owner expectations, eventwise residuals, shrinkage and a
separate downstream signal bridge. Reuse them rather than recreate BI3.

The accepted21-feature v2 vector describes relative roster/active counts, league
starter/FLEX/Superflex requirements and roster/pick sizes. It does not establish
historical positional production quality, age/role, competitive trajectory or the
actual available offer set. Do not call a roster-count residual a preference
controlled for all those circumstances. Trade-only choice research must exclude
waiver/draft outcomes; those actions may still supply properly separated evidence
or update roster continuity.

Existing archived player/pick/FAAB replay, pick lifecycle and cross-season field
coverage are reusable. Membership is not an active lineup. Supported retrospective
facts do not automatically become a contemporary Forecast, full canonical State
or at-time trade grade. Existing supplemental receipts remain independently
scoped. Neither the old seven saved-State candidates nor144 archived trade rows
are a certified combined training sample.

## Immediate correction, separate from owner-model development

Existing production observed-history signals are binary precedents. In the
November22 aggregate inspection all12 mapped owners had equal-size/consolidation
and both pick-direction precedents. Such matches often distinguish no candidates.
The counter search nonetheless adds a history queue even when identical to its
ordinary structural queue. Seen-ID deduplication prevents duplicate evaluations
but the extra queue can consume additional turn slots before another repair.

Only add a historical-precedent lane when it is a proper, nonempty subset of the
current neighbor set. Universal/empty matches leave the no-history order exactly
unchanged; selective positive precedents remain a distinct question. Preserve
all candidate identities, shortfall-repair lanes, manual priorities and full
Decision. This does not validate stronger preferences or improve universal Value.

## Next substantive milestone: context admission and validation

1. Join/deduplicate existing event sources while preserving owner tenure, source
   clocks, pre-action membership and explicit pick/slot coverage. Admit the exact
   accepted model inputs where evidenced; keep unsupported fields unknown. The
   model does not need every field required for a full historical Decision grade.
2. Inventory evidence for historical position quality/surplus, competitive
   circumstances, youth/age, picks and package structure. Prior-season actuals
   can be an explicitly dated quality proxy, not a hindsight forecast. Reuse
   historical scoring/rules and historical positions; missing or changed roles
   remain uncertain. Any new features require a versioned research comparison.
   Do not require nonexistent historical forecasts for every descriptive context.
3. Test accepted context-only expectations against pooled baselines, then test
   owner residual information on genuinely later, grouped completed choices.
   Fit priors, feature scaling and policies using earlier data only; keep both
   sides of a trade in the same fold. Record coverage, sample volume, uncertainty,
   held-out predictive loss and cross-period stability. Evidence determines the
   strength of the inference. Do not train rejection labels from unobserved offers.
4. Promote only supported contextual signals through the existing Decision/Search
   boundaries. Separate observed facts, estimates and unknowns; show how current
   team circumstances change their application. Explicit user direction controls
   the search. Native Intrinsic, Market and football Forecast remain independent.
5. Compare actual opportunities and counters with/without that specific signal
   on the same published inputs and bounded budgets. Require defensible both-team
   consequences and owner-reviewed relevance, not merely changed ordering.

Product acceptance: explain what an owner did in comparable circumstances and
what that suggests for this particular package, in plain football language.
Keep source/model detail on demand. Do not claim certainty, owner wishes, available
rejected offers or acceptance percentages that the evidence cannot support.

No new recurring resources, external APIs or paid workers are prerequisites.
No stronger preference policy, source assumption or coefficient is selected here.
