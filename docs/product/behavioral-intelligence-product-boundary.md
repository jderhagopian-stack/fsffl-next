# Behavioral Intelligence product boundary

Behavioral Intelligence is a first-class, read-only evidence and market-intelligence surface.

It answers two related questions:

1. **What has this owner actually done in the available source-backed history?**
2. **What probabilistic market intelligence can FSFFL infer about how this owner and franchise may value or respond to a specific asset or package?**

The product may present observed counts, transaction types, package shapes, positions acquired/disposed, draft-pick and FAAB activity, seasons observed, and counterparty counts. Presentation may sort, group, and summarize those facts without creating a second analytical authority.

## Governing inference principle

Uncertainty should scale the strength of an inference, not automatically suppress the inference to zero. FSFFL may produce probabilistic owner-preference estimates, acceptance probabilities, and owner-specific market intelligence when those outputs come from an explicit governed model contract. A weak sample should generally shrink toward broader priors and carry wider uncertainty; a strong and stable sample may support greater personalization.

The contract for inferred behavior should expose the evidence supporting the estimate, including available sample size, effective sample size after recency weighting where applicable, recency, stability across observed periods, evidence completeness, model/calibration version, uncertainty interval or confidence metric, and backtesting/calibration quality when available.

## Universal value versus team/owner-adjusted value

Universal FSFFL Market Value remains the common league-agnostic baseline for an asset. Behavioral Intelligence does not rewrite that universal benchmark.

FSFFL may separately produce a **Team/Owner-Adjusted Value** or equivalent owner-specific clearing-price / willingness-to-pay estimate answering: **What is this asset likely worth to this specific franchise and owner right now?**

That adjustment may incorporate governed context such as team need, current competitive state, roster construction, asset mix, replacement options, package structure, historical owner preferences, observed trading patterns, counterparty history, and other evidence that legitimately changes expected willingness to acquire or surrender the asset.

Those inputs must respect authority boundaries and anti-double-counting rules. For example, repeated historical RB acquisitions that were fully explained by persistent RB roster need should not be counted once as team need and again at full strength as an independent RB preference. Behavioral modeling should seek the residual owner tendency after controlling for contextual explanations where feasible, and uncertainty should remain visible when separation is weak.

Behavioral adjustments must not be applied as uncontrolled multiplicative boosts on top of other value or utility factors. Overlapping signals should be controlled, residualized, attributed once, or otherwise combined through a governed model so that the same underlying economic effect is counted only once. Any bounded interaction term must be explicitly modeled, evidence-backed, and validated rather than created by multiplying independent-looking factors in Presentation or downstream orchestration.

## Acceptance probability

A governed acceptance model may combine bilateral package economics, team-specific consequences, owner-specific adjusted value, behavioral tendencies, package shape, negotiation history, and uncertainty to estimate the probability that a particular offer is accepted. The output is a calibrated probability or range, not a claim that the owner will or will not accept.

Behavioral evidence may inform downstream governed consumers through explicit contracts, but Presentation itself does not calculate acceptance, Value, Decision disposition, Search authority, or Simulation outcomes.

## League-agnostic requirement

The surface and its models remain league-agnostic and team-agnostic in implementation. League-specific history, rules, roster state, scoring, and owner behavior are inputs to governed calculations rather than hardcoded product logic. No league size, lineup format, scoring rule, team identity, draft convention, or owner behavior is embedded as universal truth.

## Sleeper completed-history integration — 2026-11-16

Sleeper supplies completed transactions, not the offers that were rejected,
withdrawn or never made. Those missing outcomes will not be treated as negative
training examples. Completed-history counts cannot identify acceptance rates or
justify elevated/reduced willingness labels. This constraint applies to the
current production path; generic research contracts do not authorize odds from
this source alone. A future response model would need independently obtained,
appropriate offer/outcome evidence and validation.

The shared package-history contract binds source-backed observations to the
current owner/team, league family, exact State and admissible cutoff. It reports
sample counts, matched observed shapes, draft-pick directions and positions.
Player/pick detail uses explicit trade-only aggregates, excluding waiver and
free-agent activity. Legacy profiles retain reliable trade-shape observations;
missing trade-only detail is not reconstructed from mixed acquisition totals.
The normal existing history sync adds these optional aggregates; no request
fetches or rebuilds history.

Positive precedents may break otherwise equivalent discovery ties after economics,
priority hypotheses, package size and diversity. A separate counteroffer lane may
visit structures the counterparty has completed before. Unfamiliar structures stay
reachable. These are search hypotheses, not preference estimates or willingness
predictions. Manual priorities still control the search. Current roster needs,
competitive timelines and positional consequences remain Decision evidence; they
are not inferred owner personality. Existing context-controlled residual research
is preserved and is not replaced by raw acquisition counts.

Explore and Trade Center display the same compact observations inside existing
details. They do not label an owner as unwilling because a pattern is absent, and
they do not change Value, Forecast, Simulation or final trade disposition.

### Restart continuity

Restoring saved Behavioral profiles must also bind them to the exact restored
State's read-only lookup. A READY history record alone does not prove that Search
or Trade Center can consume it. The same binding applies to session context and
history readers; unchanged results are coalesced and the cache remains bounded.
A different stored State cannot populate the current lookup.

When legacy trade-only fields are absent, restore may derive them once in memory
from events already read by that restore, at each current owner's saved cutoff.
Use the existing aggregation and require trade-count/shape reconciliation; keep
unknown detail when it does not reconcile. This does not fetch history, write
profiles or rerun football models. The UI labels trading history explicitly and
shows a short unavailable message for a genuinely missing matching snapshot.

### Context-controlled trade research readiness

The [2026-11-17 validation](owner-context-validation-20261117.md) distinguishes
snapshot coverage, recorded continuity and model calibration from live observed
history. Trade-specific research should use the offline
`build_trade_context_calibration_dataset` adapter with all known transaction
kinds for continuity checks. Do not treat a dated snapshot alone as an accurate
pre-trade roster, combine waiver activity with trade outcomes, or call roster-count
residuals preferences controlled for competitive timeline. The current data does
not justify promoting new preference weights. Existing model authorities and live
history-based search behavior remain unchanged.
