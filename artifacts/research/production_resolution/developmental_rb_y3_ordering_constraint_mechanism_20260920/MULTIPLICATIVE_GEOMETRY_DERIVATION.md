# Multiplicative geometry derivation

The failed challenger used a common upper multiplier and a lower-group deviation:

M_U(u) = exp(A * tanh(g_U(u)))
M_L(u) = exp(A * tanh(g_U(u) + d0 + d1*z)),  z = 2(u-0.5).

It imposed:
d0+d1 <= 0 and d0-d1 <= 0.

Because d0+d1*z is affine in z, those endpoint inequalities imply d0+d1*z <= 0 for every z in [-1,1]. Since tanh and exp are monotone, they are equivalent to requiring:

M_L(u) <= M_U(u)  for every u in [0,1].

That is a constraint on the correction functions, not on the Forecast state means.

The actual Forecast ordering requirement at the only cross-group adjacent boundary is:

D1_usable(r) * M_L(u_r) < D1_starter(r) * M_U(u_r).

Equivalently:

M_L(u_r) / M_U(u_r) < D1_starter(r) / D1_usable(r).

The right side is greater than one because D1 already has ordered state means. Therefore final state ordering can remain valid even when M_L > M_U.

Diagnostic unconstrained optima require M_L/M_U roughly 1.055 to 1.158 across the full percentile domain. Historical D1 starter/usable separation is much larger: the minimum training-support ratio is about 1.379 and the minimum evaluation-support ratio is about 1.449. Applying the unconstrained correction geometrically produces zero final-ordering violations on all historical training/evaluation support, with the smallest final starter/usable ratio still about 1.209 in training support and 1.262 in evaluation support.

Thus the preregistered endpoint constraints consumed real D1 ordering headroom that Forecast did not need them to consume.