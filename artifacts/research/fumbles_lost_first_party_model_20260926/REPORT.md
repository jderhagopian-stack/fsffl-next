# First-Party FUMBLES_LOST Model Research

Design/model/gates were frozen before 2026 named-player shadows.

## Result
Selected model: calibrated_position_opportunity_rate
Production-ready: True

- position_opportunity_rate: FAIL; RMSE=0.9566; MAE=0.5963; bias=0.2832; zero_gap=0.1084; reasons=bias,zero_calibration
- calibrated_position_opportunity_rate: PASS; RMSE=0.8105; MAE=0.4868; bias=0.0509; zero_gap=0.0347; reasons=none
- player_history_shrunk: FAIL; RMSE=1.1103; MAE=0.6231; bias=0.2926; zero_gap=0.0887; reasons=rmse_vs_zero,rmse_vs_position_game,bias,zero_calibration,2025_rmse_stability
- player_history_plus_current: FAIL; RMSE=1.2126; MAE=0.6516; bias=0.2946; zero_gap=0.0814; reasons=rmse_vs_zero,rmse_vs_position_game,bias,zero_calibration,2023_rmse_stability,2024_rmse_stability,2025_rmse_stability

## Baselines
- zero_omission: RMSE=1.0425; MAE=0.4118; bias=-0.4118
- position_game_rate: RMSE=1.0475; MAE=0.7013; bias=0.3481

## Current coverage
{"board_rows": 335, "identity_coverage": 0.9761194029850746, "mapped_gsis": 327, "passes": true, "tier_counts": {"cold_start": 1, "current_only": 28, "history_only": 40, "history_plus_current": 258, "unmapped": 8}}

## PIT boundary
OOT folds reconstruct a Week-2 cutoff using only prior seasons plus Weeks 1-2 of the held-out year. The 2026 production artifact is valid only from its actual build/evaluation cutoff and is not eligible as 2026 preseason evidence or historical backfill.
