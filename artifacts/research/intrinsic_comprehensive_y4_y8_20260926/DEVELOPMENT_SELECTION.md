# Comprehensive Y4-Y8 Development Selection

Status: **DEVELOPMENT SELECTION FROZEN BEFORE UNTOUCHED FINAL HOLDOUT.**

Selected architecture: `hierarchical_blend`

Development architecture score versus incumbent baseline: **-0.052774**.

Frozen architecture:
- **75%** position × horizon specialist prediction;
- **25%** shared continuous-horizon prediction;
- shared component: `global_continuous|football_plus|two_part_ridge`;
- specialist cell route is frozen in `FROZEN_ARCHITECTURE_CANDIDATE.json`.

The development selector did **not** preserve one universal post-H3 model. Richer PIT football evidence changed the candidate architecture materially, especially at QB, while several WR/RB cells shrank back to the old Forecast-only two-part baseline when extra complexity was not stable/material.

Final holdout was not scored during selection. Current named-player shadows were not generated.

Frozen untouched final holdouts:
- Y4: base seasons 2020–2022;
- Y5: 2019–2021;
- Y6: 2018–2020;
- Y7: 2017–2019;
- Y8: 2016–2018.

Frozen fallback if the selected architecture fails final confirmation:
`specialist|forecast10|two_part_ridge`.

Frozen confirmation requires:
- aggregate RMSE no worse than 1.02× fallback;
- aggregate top-tail RMSE no worse than 1.05× fallback;
- at least two aggregate wins among RMSE / MAE / tail RMSE / Spearman;
- no position × horizon RMSE catastrophe above 1.15× fallback;
- no position × horizon tail-RMSE catastrophe above 1.20× fallback;
- no candidate redefinition after holdout.

Development workflow:
- run `36263509294`;
- head `c46d060f4914a651069466c5847cf8813ba9e325`;
- artifact `10913506052`;
- digest `sha256:4ec805f2ea33c86b7790f7fc518f3610f60a09b500cbd454ad0978ac9284476a`.

Next authorized action: run the separate untouched final-holdout evaluator without altering candidate definitions.
