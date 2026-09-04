# Evidence and Parameter Lifecycle

## Principle

No material parameter exists merely because legacy FSFFL used it. Every parameter must have a reason to exist, an authority owner, and an update mode.

## Update modes

- `STATIC_RULE_DEFINED` — fixed by league rules, mathematics, or invariant architecture.
- `STRUCTURALLY_DERIVED` — computed deterministically from other authoritative state.
- `EMPIRICALLY_ESTIMATED` — estimated from a defined evidence set.
- `EVIDENCE_UPDATING` — periodically re-estimated as additional evidence arrives.
- `BOUNDED_PROVISIONAL_PRIOR` — temporary explicit prior used when the effect is real enough to model but evidence is not yet sufficient for precise calibration.
- `CHALLENGER_ONLY` — experimental estimate that cannot drive production decisions.

## Required metadata

A material parameter should record, as applicable:

- stable parameter identifier;
- human-readable definition;
- owning layer/module;
- update mode;
- estimate or distribution;
- uncertainty/confidence interval;
- units and scale;
- evidence references;
- estimation method;
- effective date/as-of date;
- model version;
- dependencies;
- lifecycle state;
- calibration history;
- licensing/provenance constraints.

## Promotion standard

A challenger should be promoted only when the relevant evidence supports improvement. Evaluation may include predictive accuracy, historical transaction fit, out-of-sample behavior, simulation consistency, stability, uncertainty calibration, and football-economic sanity.

Legacy agreement is not a promotion criterion.

## Double-counting contract

Before introducing a new parameter or adjustment, identify the real-world effect it represents and all existing pathways through which that effect may already influence forecast, value, or utility. Overlapping effects must be residualized, consolidated, or rejected rather than stacked.

## Provisional priors

A lack of perfect evidence does not require deleting a material real-world effect. A bounded provisional prior is acceptable when:

1. the effect has a defensible causal/economic rationale;
2. ignoring it would create a known structural omission;
3. the prior is intentionally conservative and uncertainty is explicit;
4. it cannot silently duplicate another authority channel; and
5. the architecture makes later empirical updating straightforward.

## Historical integrity

Parameter fitting against historical decisions must use information available at the historical as-of point. Current values, future player outcomes, realized pick slots, or later market information must not leak into historical features except as labeled target/outcome variables.
