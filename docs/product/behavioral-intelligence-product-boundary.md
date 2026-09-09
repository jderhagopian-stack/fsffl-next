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
