# Validation Framework

FSFFL NEXT is optimized for validated improvement, not legacy parity.

## Validation layers

Every material model component should be tested at the layers relevant to its responsibility:

### 1. Contract validity
- schema correctness;
- units and types;
- missing-data behavior;
- deterministic behavior where expected;
- authority-boundary compliance.

### 2. Internal coherence
- monotonicity where economically required;
- conservation/identity checks;
- no duplicated signal paths;
- sensible behavior under controlled perturbations.

### 3. Historical evidence
- point-in-time backtests;
- out-of-sample evaluation when sample size permits;
- calibration and error decomposition;
- subgroup/position/horizon performance.

### 4. Sanity cases
Maintain a governed set of known failure modes and intuitive edge cases. These do not replace empirical evidence, but they protect against obviously incoherent behavior.

### 5. Decision utility
Evaluate whether a change improves the decisions the platform is meant to support, including bilateral transactions, roster construction, contender/rebuilder contexts, and uncertainty-sensitive choices.

### 6. Performance and reliability
- runtime;
- memory;
- cache correctness;
- concurrency safety where relevant;
- reproducibility;
- graceful degradation under provider gaps.

## Legacy comparisons

Legacy FSFFL is a useful comparator and source of test cases, not a gold standard.

When NEXT differs materially, record:

- legacy output;
- NEXT output;
- source of difference;
- evidence/rationale;
- uncertainty;
- disposition: adopt NEXT, revise NEXT, retain legacy concept, or investigate.

## Promotion standard

A challenger should earn authority through the strongest evidence reasonably available. A known real effect should not be dropped merely because perfect identification is unavailable; when justified, use a bounded documented provisional prior with a plan for empirical updating.

## Anti-overfit rule

Historical fit alone is insufficient. Prefer parsimonious mechanisms, held-out testing, shrinkage/regularization where appropriate, and stability across time and league contexts.

## Reporting

Validation artifacts should be machine-readable where practical so future CI can block promotion when required tests regress.
