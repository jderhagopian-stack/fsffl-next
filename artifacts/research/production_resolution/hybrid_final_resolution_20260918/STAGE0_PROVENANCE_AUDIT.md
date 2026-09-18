# Stage 0 — Ordered-State Recombination Execution-Provenance Audit

Status: PASS for durable prediction-level evidence; proceed to bounded H1-H3 study.

Live refs at audit start:
- research/future-state-resolution-phase34-resume: 86043a6610bc4dce79a159502f24cb70a762fabc
- main: 53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76
- PR #147: open/unmerged; head 3e63cd61602d0832acf0a30dcc5bee0b13ceeb63

Recovered exact surviving outputs:
- recombination_prediction_rows.csv — 41,344 rows; SHA-256 dbd1b1b5fd7fe7c6c43c2e6bda417db192c852f136ac704a7a5abb48fae2288b
- fold_metrics.csv — SHA-256 2b97211a3381dffb321e04caac8681daa70bc16cf0b7957a45be60a0428eca6b
- cohort_metrics.csv — SHA-256 4bcccd0198fa73ca83e6c98930bf9d4029f938865cf172cb2560304e68ade20c
- role_loss_stress.csv — SHA-256 129686062acce51ec974ee05f194de7542419c0bd01ec19ec12ad6e99150c0b1
- position_metrics.csv — SHA-256 49f0da5a7f1c14d5bc540ada745634793a7fbf9cd8e9a58012c4f28e9e3e0e29
- nonpersistence_stress.csv — SHA-256 eeeeabc5e9f6cdf83c2d50fbc1c09ba5da874db545d0757aacfc82a58ea18a14
- ARCHITECTURE_SPECIFICATION.json — SHA-256 197acd61b3420c6664e171c00a24e7d2a19b91ee1fcf8e2ec91ab6e307dee9cc
- management PDF — SHA-256 2debd4f11e20871d5de24d279d36589120446cc155c3d61df7e1aa17caf38e8f

Evaluation universe row counts per candidate/horizon:
- early: 1,664
- mid: 1,129
- validation: 1,165
- non-pristine 2021-2022: 1,210

The prediction-level file contains Candidate B, FrozenForecast, R1 and R2 on identical rows. The prior reported active, top-10%, and role-loss MAEs were recomputed directly from those persisted prediction rows and match the prior report to floating-point precision.

Execution provenance clarification:
- The preceding recombination run DID perform model fitting. It reconstructed the frozen ordered-state machinery from surviving governed code/evidence and fit Candidate B, R1 and R2 inside each chronological training cutoff.
- Historical PIT evidence was loaded from the recovered Phase-2 panel/q3 artifacts. Existing frozen architecture/routing constants were reused; fold-specific state probabilities and candidate production predictions were recomputed in that run.
- The CSV and PDF artifacts above were newly produced by that execution.
- Measured wall-clock runtime was not durably recorded/recoverable; do not invent one.

This audit does not rerun or alter the recombination study. It verifies the durable outputs already produced and is sufficient to use Candidate B and R2 persisted predictions as frozen ensemble anchors for the authorized H study.
