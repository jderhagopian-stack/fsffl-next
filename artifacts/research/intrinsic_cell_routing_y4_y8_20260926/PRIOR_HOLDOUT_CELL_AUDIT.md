# Prior Sealed-Holdout Cell Audit

This is a descriptive audit of the already-exposed comprehensive final holdout. It is **not** an input to the corrective routing policy.

Classification rule, frozen for this audit:
- `materially_favors_richer`: richer RMSE <= 0.98× baseline and richer tail RMSE <= 0.98× baseline, with at least two wins among RMSE / MAE / tail RMSE / Spearman;
- `materially_favors_baseline`: richer RMSE >= 1.05× baseline, or richer tail RMSE >= 1.10× baseline, or richer wins no more than one of the four metrics;
- otherwise `mixed_or_indistinguishable`.

Result:
- richer: 10 / 20 cells;
- baseline: 2 / 20 cells (QB Y8 and RB Y6);
- mixed/indistinguishable: 8 / 20 cells.

The QB Y8 failure remains real and visible: RMSE ratio 1.2904× and MAE ratio 1.4906× versus the baseline. That failure invalidated blanket promotion of the frozen 75/25 architecture. It does not, by itself, establish authority for the baseline in unrelated cells.

The corrective rolling-validation workflow must not read this audit for route selection or policy tuning.
