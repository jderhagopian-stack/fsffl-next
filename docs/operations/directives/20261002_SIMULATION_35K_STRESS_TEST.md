# 2026-10-02 — Simulation 35k vs 50k stress test

## Status
**MANAGEMENT DIRECTIVE — BOUNDED POST-CLOSEOUT AUTHORITY RE-EVALUATION**

Simulation 2.0 items #324-#331 remain accepted and are not reopened. Production Simulation authority remains **50,000 canonical runs** unless Management explicitly approves a later change.

This directive authorizes one bounded research/evidence stress test because item-8 convergence showed 35,000 runs as the only lower count with a potentially attractive speed/fidelity tradeoff.

## Question
Does **35,000** remain decision-stable relative to the existing **50,000** authority under deliberately difficult but governed league states, or does the extra 15,000 runs materially protect product outputs near important boundaries?

This is not a general Simulation redesign and not another broad convergence study.

## Required comparison
Primary candidates:
- 35,000 runs;
- 50,000 runs, current production authority.

Research reference:
- 100,000 runs for same-root comparison only.

Optional controls such as 25,000 may be included only if cheap and useful for locating the convergence knee. Do not expand into 75,000 unless a result is genuinely ambiguous.

Use the production NumPy/PCG64 batched protocol and preserve all accepted model, replay, rules, persistence and common-world semantics.

## Stress cases
Use multiple governed fixtures/states chosen to make Monte Carlo instability more likely, including at least:
1. **Razor-thin playoff bubble** — several teams with nearly indistinguishable qualification odds / expected wins.
2. **High-parity league** — compressed team-strength distribution producing many close standings outcomes.
3. **Tail championship case** — credible low-probability title outcomes where sampling noise could matter.
4. **Future-pick boundary case** — origin-team slot distributions concentrated near meaningful exact-slot / early-mid-late boundaries.
5. **Near-zero scenario delta** — small authorized counterfactual whose sign could plausibly flip from Monte Carlo noise.
6. **Material scenario delta** — clear trade/availability-style competitive change to confirm large signals remain stable.
7. **Postseason-structure variation** — exercise more than one supported governed playoff shape where practical, including bye/no-bye structures.

Prefer authentic current league-derived states where they can be sanitized/replayed without introducing uncontrolled live-data drift; otherwise use deterministic governed fixtures. Do not manufacture unsupported custom rules just to create difficulty.

## Replication
Use enough independent roots to detect seed sensitivity beyond the original single-fixture eight-root study. Preserve same-root 100k reference pairing.

The test should be computationally bounded. Increase roots/fixtures only when needed to resolve an observed ambiguity; do not turn this into an open-ended benchmark campaign.

## Decision-relevant outputs
For 35k and 50k versus same-root 100k, report at minimum:
- expected wins;
- playoff probability;
- championship probability;
- finish-position distribution;
- future-pick-slot distribution;
- scenario-delta magnitude and sign;
- independent-root dispersion;
- runtime.

Also explicitly test whether 35k versus 50k changes any **product-relevant conclusion**, including where applicable:
- displayed/ranked ordering of closely matched teams;
- rounded user-visible probabilities;
- playoff/competitive classification inputs;
- exact-slot / early-mid-late pick summaries;
- downstream Decision/Opportunity materiality or disposition when the Simulation delta is an input.

Do not invent a new downstream decision rule for this study. Use existing governed consumers only.

## Interpretation / promotion rule
The study must distinguish:
1. numerical error;
2. practical product materiality;
3. sign/rank/classification stability;
4. runtime savings.

A lower count is not promoted because its average error is small. Any case where 35k changes a decision-relevant sign, ordering, classification, disposition, or materially visible probability while 50k is stable must be surfaced plainly.

If 35k remains product-equivalent across the bounded stress set and preserves meaningful runtime savings, return a **Management proposal** to consider changing production authority. Do not change production count, adaptive rules, model identity or deployment config in the stress-test PR itself.

If the evidence is mixed or 35k fails a meaningful boundary case, retain 50k and close the study without further count hunting.

## Validation / closeout
Research/evidence only:
- deterministic harness coverage;
- exact-head tests / full CI appropriate to touched code;
- bounded P1/P2 review of study methodology and aggregation;
- durable artifacts with fixture identities, roots, raw summaries and interpretation.

No Render deploy or physical acceptance is required unless the implementation unexpectedly touches production runtime behavior.

## Sequencing
Temporarily hold the next origin-aware draft-pick Value implementation until this bounded stress test reports to Management. After the result:
- if 50k is retained, resume origin-aware draft-pick Value immediately;
- if Management approves 35k, perform the separate production-authority implementation/promotion change first, then resume Value.

Long-Term Intrinsic and later PIT historical-market work remain downstream and are not reopened by this study.
