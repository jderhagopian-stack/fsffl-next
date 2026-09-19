# NEXT-5 Exit Review

This is the governing closeout matrix for NEXT-5 Trade Decision.

## Promotion states

- **AUTHORITATIVE** — validated enough to be consumed as default NEXT behavior.
- **AUTHORITATIVE_CONDITIONAL** — authoritative when supplied an explicit governed upstream/policy input; no hidden default is allowed.
- **PROVISIONAL_GOVERNED** — real concept with incomplete evidence; explicit, versioned, and future-updatable.
- **CHALLENGER** — testable but non-authoritative.
- **ABSENT_BY_DESIGN** — intentionally not fabricated when evidence is insufficient.
- **OUT_OF_SCOPE** — belongs to a downstream NEXT layer.

## Current classification

| Component | Status | Basis | NEXT-6 may consume? |
| --- | --- | --- | --- |
| Bilateral proposal contracts | AUTHORITATIVE | Immutable canonical player/pick/FAAB legs with duplicate and identity checks | Yes |
| Trade state transition | AUTHORITATIVE | Ownership, FAAB, PIT, duplicate ownership, and source immutability checks | Yes |
| Bilateral NEXT-4 delta binding | AUTHORITATIVE | Both teams remain separate; no recomputation or master score | Yes |
| Typed transaction economics | AUTHORITATIVE | Market/intrinsic/acquisition/sale concepts remain separate | Yes |
| Expected package means | AUTHORITATIVE | Additive only on compatible NEXT-3 scales; missing evidence explicit | Yes |
| Package economic uncertainty | ABSENT_BY_DESIGN | No covariance authority; uncertainty is not fabricated | Yes, as unavailable |
| Complete-evidence economic net | AUTHORITATIVE | Received-minus-sent only within same concept/scale and only with complete evidence | Yes |
| Exact directional decision shape | AUTHORITATIVE | Uniform gain/loss, mixed, neutral, incomplete; no weights | Yes |
| Owner strategic posture overlay | AUTHORITATIVE | Posture sits beside calculated consequences and cannot rewrite them | Yes |
| Competitive/economic materiality policy contracts | AUTHORITATIVE | Explicit version/evidence/provenance and no hidden defaults | Yes |
| Material assessment using supplied policy | AUTHORITATIVE_CONDITIONAL | Future leakage and economic scale compatibility fail closed | Yes, with explicit policy |
| Production materiality thresholds | ABSENT_BY_DESIGN / PENDING CALIBRATION | No arbitrary thresholds promoted merely for completeness | No automatic action authority until governed policy supplied |
| Acceptance evidence contracts | AUTHORITATIVE | Point-in-time evidence, uncertainty interval, lifecycle status, future leakage checks | Yes |
| Acceptance probability model | ABSENT_BY_DESIGN / CHALLENGER PENDING | No admissible NEXT calibration dataset yet; no fabricated 50% prior | Yes only as NOT_ESTIMATED/unknown |
| Non-probabilistic negotiation feasibility shape | AUTHORITATIVE | Counterparty-dominated, mutual-gain candidate, mixed, incomplete, neutral | Yes |
| Conservative trade disposition | AUTHORITATIVE_CONDITIONAL | Requires explicit material assessment; missing evidence withholds action | Yes, with governed materiality policy |
| Strategic resolution of mixed tradeoffs | PROVISIONAL_GOVERNED / NOT APPLIED | Owner posture recorded; no unvalidated posture weights or scalar preference mapping | Yes as unresolved mixed evidence |
| Candidate/package search | OUT_OF_SCOPE | NEXT-6 Search/Optimization | No |
| Reports/presentation | OUT_OF_SCOPE | NEXT-7/8 | No |

## Key safety properties

- A player or pick cannot be traded by a team that does not own it.
- FAAB cannot be overspent.
- The source LeagueState is never mutated.
- NEXT-5 never alters NEXT-2 forecasts, NEXT-3 values, or NEXT-4 simulation/team utility.
- Market price is not relabeled as franchise utility.
- Missing pick/FAAB/economic evidence is not treated as zero.
- Package uncertainty is not invented from an independence assumption.
- Missing decision channels cannot promote a proposal to mutual gain.
- A counterparty that is uniformly worse on complete observed channels is surfaced as counterparty-dominated rather than assumed likely to accept.
- Owner posture cannot rewrite calculated consequences.
- Acceptance probability remains unknown until a calibrated model exists.
- Materiality thresholds cannot be hidden in decision code.
- NEXT-5 has an automated import boundary preventing Search/Analytics/Presentation authority leakage.

## Controlled sanity coverage

Current tests cover:

- legal player/pick/FAAB transfers and immutable state;
- wrong-owner and overspend rejection;
- duplicate asset and future-state rejection;
- bilateral team identity and scale/concept integrity;
- complete vs partial economic evidence;
- economic received-minus-sent symmetry;
- uniform mutual gain, one-sided loss, mixed short-/long-term tradeoffs, neutral and incomplete evidence;
- resilience direction semantics;
- explicit materiality thresholds and future-policy rejection;
- owner posture separation;
- counterparty-dominated negotiation feasibility;
- conservative SUPPORT / DECLINE / COUNTER_OR_REVIEW / NO_CLEAR_ADVANTAGE / INSUFFICIENT_EVIDENCE dispositions;
- downstream import-boundary protection.

## Remaining empirical work

### Materiality calibration

The code supports explicit, versioned policies but NEXT does not yet have evidence-backed production thresholds for:

- expected-win delta;
- playoff-probability delta;
- first-place-probability delta;
- lineup fragility delta;
- economic value delta on a named value scale.

These should be estimated/calibrated rather than selected merely to finish a checklist. Until then, exact directional evidence remains authoritative and material action dispositions require an explicitly supplied governed policy.

### Acceptance / negotiation calibration

The acceptance evidence and probability contracts are ready, but there is not yet an admissible NEXT point-in-time dataset containing enough positive and negative negotiation outcomes to promote a probability model.

Until calibrated:

- acceptance is `NOT_ESTIMATED`;
- clear counterparty domination remains visible;
- mixed/incomplete cases remain uncertain;
- downstream search must not convert unknown acceptance into a positive feasibility claim.

## Real-league validation

The integrated live-league adversarial/beta pass remains deferred until a networked runtime is available. This is not hidden validation: no live league output has been observed yet. When available, the shared runtime path should exercise State -> Forecast -> Value -> Team Utility -> Trade Decision -> Search/Analytics and convert any generalizable defect into regression coverage.

## Exit recommendation

NEXT-5's **architecture and deterministic decision mechanics** can be closed once exact-head CI and changed-file scope are clean. The lack of calibrated production materiality and acceptance probabilities should remain explicit governed gaps rather than be filled with arbitrary constants.

NEXT-6 may begin search/optimization over NEXT-5's structured outputs, but it must preserve these rules:

1. unknown acceptance remains unknown;
2. conditional dispositions require an explicit governed materiality policy;
3. counterparty-dominated proposals may be explored diagnostically but cannot be promoted as realistic actionable opportunities without contrary acceptance evidence;
4. NEXT-6 may search over values and utility but may not rewrite them.
