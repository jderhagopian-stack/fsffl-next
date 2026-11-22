# Contextual Owner Intelligence: model-input readiness

The standing delivery sequence is in the
[roadmap](../operations/PRODUCT_ROADMAP.md#standing-delivery-sequence--agreed-2026-11-22).
This is the first input-layer increment of contextual Owner Intelligence, not a
new owner model or completion of that milestone.

## Reuse one feature definition

`behavioral/context_inputs.py` describes exactly the21 inputs already consumed by
`context_expectation_v2.py`. The existing full canonical-context path now calls
that same numerical projection. Frozen vector and native model regressions check
parity; nearest-neighbor estimation, prior-only training, residuals, policies and
model versions are unchanged. No competitive/quality feature is silently added.

A partial context can preserve known membership, position counts, league means
or lineup requirements while retaining unknown active counts or pick inventory.
The report identifies each missing feature; it cannot return a complete vector
until all model-required facts are present. A known zero is valid, an unknown is
not zero. Invalid counts, duplicates and non-finite facts are rejected.

This separates the exact model's needs from full historical State construction:
FAAB balance, full player forecasts and market prices are not among these21
inputs. Do not manufacture them to represent this model's readiness. Conversely,
this report does not certify owner identity, source availability, historical
continuity or action clocks. The existing source and trade-context integrity
guards still own those checks; complete numbers alone do not admit training data.

## What existing evidence does and does not support

The accepted archive-only field-coverage baseline has144 trade rows and96
consistent membership contexts, not144 complete model observations. It provides
neither complete active-placement/historical-position evidence nor full pick
counts at every action boundary. Creation/completion clocks also differ. Existing
supplemental2023 receipts and separate saved-State evidence must be reused and
reconciled before reporting combined readiness; counts must not be summed.
These are retained prior findings, not a new raw-data run in this increment.

Examples on controlled inputs:
- Membership-only roster size gives1 of21 numerical inputs, not full readiness.
- Evidenced total position counts, league means, direct requirements, roster size,
  FLEX and Superflex give11 of21; missing active context and pick counts remain
  individually visible.
- A complete native context gives21 of21 with the unchanged frozen vector.

These examples do not claim that the archive supplies all fields in the second
case. Archived rules need their existing season-specific normalization; positions
and active slots require their own dated evidence. No aggregate membership flag
or today's roster may populate unknown fields.

## Acceptance and continuation

This increment accepts numerical projection/missingness only. Focused tests
cover golden-vector parity, retained source-context guards, no FAAB dependency,
unknown versus zero, incomplete inputs and invalid facts. Nothing fetches,
replays, fits, persists or publishes during a readiness check; work is bounded by
four positions and21 features. It introduces no service, connection, provider
call, cache, recurring expense or web work.

Next: feed admitted source facts from the existing archived and saved-State routes
through this projection, preserving event/owner identity and dual clocks. Produce
per-feature and per-event coverage; then run grouped chronological comparisons of
the existing model against pooled/context-only baselines. Where original context
features cannot be evidenced, an alternative feature set requires explicit
versioned research rather than hidden zero-filling. Use supported prior actuals
for clearly labeled historical quality context where appropriate, without
inventing historical forecasts. Stronger inference and search influence remain
behind their validation gates. Physical usefulness and held-out predictive
quality are not established by these input tests.
