# Final research conclusion

Classification: **B. MECHANISM WAS CORRECT, BUT CHALLENGER IS NOT STRONG ENOUGH**.

The single preregistered gap-aware prospective-log1p challenger was fit at all nine 2014-2022 origins using only earlier prospective D1 residuals resolved by each origin. Exact D1 replay parity passed (max absolute difference 8.53e-14); D1 probabilities/routing/scale remained unchanged; and there were zero final-state ordering violations.

Full-cell CRPS gain (D1 - challenger): +0.0145, clustered 95% interval [-0.4045, +0.3399], with 6/9 origins improved and median origin gain +0.2232. MAE gain: +0.9366.

Continuous-magnitude IMCE improvement: overall +0.1397 (+38.2%); upper +0.1103; lower +0.0922. Low/mid CRPS gain +0.0873; low/mid IMCE improvement +0.2480.

The corrected parameterization did express nonzero lower-group deviations: median d0=-0.1812, median d1=+0.0044. Max |tanh(h)| on evaluation rows was 0.2686; there were zero ordering violations.

Failed material gates: full_cell_crps, continuous_magnitude_calibration, individual_state_no_new_failure, coverage, temporal_and_player_influence. No alternate candidate, penalty, coordinate, grouping, amplitude, state-probability change, merge, deployment, or production promotion was attempted. Source-2023 -> target-2026 remains untouched.