# Role-loss / collapse error-economics diagnostic — management checkpoint

Status: COMPLETE / STOP FOR MANAGEMENT.

No model fitting or model change occurred. This diagnostic reused the persisted 41,344-row aligned recombination prediction evidence (SHA-256 dbd1b1b5fd7fe7c6c43c2e6bda417db192c852f136ac704a7a5abb48fae2288b).

## Findings
- Exact pre-holdout role-loss cohort: Y2 315/2376 active observations (13.3%); Y3 271/1911 (14.2%).
- Candidate B role-loss absolute error is 10.6% of all active Y2 AE and 10.9% of Y3 AE.
- B's safety advantage over R2 is concentrated in severe statistical collapses: realized retention <25% accounts for 63.2% of Y2 and 61.7% of Y3 B-vs-R2 role-loss AE advantage.
- Repository-governed evidence cannot establish causal events or source-time foreseeability (injury, benching, transaction, retirement, suspension, etc.). Causal taxonomy therefore stops at UNKNOWN rather than inferring causes from production.
- Population total AE: R2 slightly better Y2 (97,562.9 vs B 98,417.8); B slightly better Y3 (82,485.7 vs R2 83,264.8).
- Deep-collapse-excluded sensitivity (diagnostic only): R2 MAE better at both horizons (38.98 vs 40.90 Y2; 41.39 vs 42.80 Y3).
- Evaluation-policy finding: evidence does not support automatic hard-veto treatment of role-loss MAE. Role loss should remain an explicit stress test / softer evaluation consideration unless management separately authorizes point-in-time causal reconstruction and finds source-time forecastability/economic importance sufficient to justify special veto power.
- No production correction implemented.

Protected refs at start: research branch 8839cfad99ec4850782d5bc720784d0672012472; main 53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76; PR #147 open/unmerged head 3e63cd61602d0832acf0a30dcc5bee0b13ceeb63.

STOP.