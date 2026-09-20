# Final mechanism conclusion

Classification: **A. PARAMETERIZATION CONFLICT IDENTIFIED - ONE NATURAL CHALLENGER JUSTIFIED**

The failed challenger was not evidence that the upper/lower feasibility signal was false. The exact constrained fit is reproduced: both endpoint constraints bound in all nine origins and forced d0/d1 to numerical zero.

The unconstrained exact objective consistently wants d0 > 0 and d1 < 0. That means the lower correction is larger than the upper correction at low/mid magnitude but falls faster with magnitude. The preregistered constraint prohibited this because it required M_L <= M_U everywhere.

That prohibition was stronger than Forecast ordering requires. Final ordering only needs D1_usable*M_L < D1_starter*M_U. Across historical support, the unconstrained lower/upper multiplier ratio never exceeds about 1.158, while the minimum D1 starter/usable ratio is about 1.379 on training support and 1.449 on evaluation support. There are zero historical final-ordering violations under the unconstrained geometry.

The mechanism is not primarily unsupported full-domain endpoints: developmental-RB source percentiles span about 0.003 to 0.997. The more important representation conflicts are (1) ordering the correction functions instead of the final state means and (2) fitting raw log-ratio in-sample residuals even though the stable feasibility signal was established on prospective log1p residuals.

One natural unfitted successor is therefore justified: a gap-aware log1p partial-pooling calibration trained on prior-origin prospective residuals, with final ordering guaranteed from each row's D1 starter/usable gap. It keeps four parameters, the prior regularization, frozen D1 probabilities, continuous magnitude, and no threshold states.

No successor was fit or scored in this task. D1 remains the control. PR #147 and protected main remain untouched. Source-2023 -> target-2026 remains uninspected.