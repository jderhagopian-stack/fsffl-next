# Forecast Baseline Attribution - Exact Equation and Feature Lineage

Date: 2026-09-20  
Diagnostic authority only. No production authority changes.

## Frozen authority

- PR #147 recovered at `34470dce369df2c9d5454ebbd481317c5ab76d12`.
- Protected main recovered at `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- P0 package SHA-256: `ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7`.
- Final route authority: `p0-final-route-authority-v1:cf5e3c0d375c`.
- Frozen raw preseason stats: 1,675 observations / 335 players.
- Frozen raw-array SHA-256: `4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d`.
- Current-source SHA-256: `eda43a5e297ffe46550af5c3fbf98a1d32545fc15925a9e49c6620427043307a`.

Authoritative implementation sources:
- `src/fsffl/product/p0_forecast_runtime.py`
- `src/fsffl/product/p0_frozen_assets.py`
- `src/fsffl/product/i1_player_scoring.py`
- `src/fsffl/product/private_beta_shapley_runtime.py`
- `src/fsffl/value/live_intrinsic_calendar.py`
- `src/fsffl/value/shapley_intrinsic.py`
- `src/fsffl/value/shapley_intrinsic_contract.py`
- `src/fsffl/product/simulation_runtime.py`

## 1. State / survival layer

For a fitted binary component:
```
z = intercept + sum_j beta_j * x_j
P = sigmoid(z)
```

Persistence probability is scored separately from the ordered positive-state thresholds. Ordered positive-state cumulative probabilities are clipped to enforce monotonicity:
```
u = P(useful+)
s = min(u, P(starter+))
p = min(s, P(premium+))
e = min(p, P(elite))
```

Conditional positive-state mass:
```
q_depth   = 1 - u
q_usable  = u - s
q_starter = s - p
q_premium = p - e
q_elite   = e
```

Final state probabilities:
```
P(out)       = 1 - persistence
P(state=k)   = persistence * q_k
```
followed by normalization.

### Population/group anchors in state probability

The minimal generic anchor is the fitted intercept plus position, source-state, and horizon categorical terms. The full model then adds individual evidence.

### Player-specific state-probability authority

Depending on layer and route, the exact runtime can use:
- current source production: `lp = log1p(source_points)/6`
- prior production: `lprev = log1p(prior_points)/6`
- source-minus-prior difference: `dpts = clip((source-prior)/100,-2,2)`
- prior coverage
- age band or exact position-specific age transforms
- experience band and continuous experience
- source role/opportunity/game evidence when available
- source-state percentile terms
- premium/elite high/low percentile terms
- governed QB residual-memory terms for prime/aging QBs
- missing-evidence coverage controls fixed by the frozen P0 current-source path.

## 2. Conditional production layer

Every continuous production input is standardized using the frozen fitted model scaler:
```
z(x) = (x - fitted_mean_x) / fitted_sd_x
```

The production prediction is:
```
mu = max(0, intercept + sum_j beta_j * f_j)
```

### D0

D0 produces one common positive-state mean:
```
mu_depth = mu_usable = mu_starter = mu_premium = mu_elite = mu_common
```

D0 feature families:
- position
- source state
- source log-points and position interaction
- source percentile and position interaction
- age and position interaction
- experience and position interaction
- prior-1 production and position interaction
- prior-1 coverage.

### D1

D1 produces a different mean for each positive future state:
```
mu_k = max(0, intercept + beta_anchor(position, source_state, future_state)
                 + beta_source(source magnitude, percentile, interactions)
                 + beta_age_exp(age, experience, interactions)
                 + beta_history(prior1, prior2, coverage, interactions))
```

D1 adds:
- future-state dummy
- position x future-state dummy
- source log-points x future-state
- source percentile x future-state
- internal prior-2 mean/gap and position interactions
- prior-2 coverage.

There is no separate external prior-two layer after P0; these are internal D1 fitted features.

## 3. Exact baseline definition used by this diagnostic

For conditional-production attribution, **population/state anchor** means:
- fitted intercept
- position categorical
- source-state categorical
- and for D1, future-state + position-by-future-state terms.

The diagnostic **player-specific production evidence** families are:
1. source magnitude / percentile;
2. age / experience;
3. prior-1 / prior-2 history and coverage.

The anchor-only counterfactual leaves the fitted model and all routing untouched but zeroes those three player-specific feature families. It is an attribution device only; it is not a fitted alternative.

For state-probability attribution, the minimal anchor retains intercept + position + source state + horizon and zeroes individual numeric/history/age/role/percentile evidence. Again, this is a read-only sensitivity counterfactual.

## 4. Expected-value reconstruction

For horizon h:
```
E[Y_h | player] =
    P(depth)   * mu_depth
  + P(usable)  * mu_usable
  + P(starter) * mu_starter
  + P(premium) * mu_premium
  + P(elite)   * mu_elite
```

Conditional-active production:
```
E[Y_h | active, player] = E[Y_h | player] / (1 - P(out))
```

## 5. League-specific scoring translation

The P0 internal coordinate remains standard/non-PPR. The connected-league translation is player-specific and applied once:
```
m_player = connected_league_Y1_points / standard_Y1_points
mu_state,connected = m_player * mu_state,standard
```
The state probabilities do not change. Expected points are recomputed from the translated state means and unchanged probabilities. There is no position-average translation in the promoted P0 path.

## 6. Route authority audited

Y2:
- QB developmental/established/veteran: D1
- RB developmental/established/veteran: D1
- WR developmental/established/veteran: D1
- TE developmental/established/veteran: D1

Y3:
- QB developmental/established/veteran: D1
- RB developmental: D1
- RB established: D1
- RB veteran: D0
- WR developmental/established: D1
- WR veteran: D0
- TE developmental/established: D1
- TE veteran: D0

The final route authority differs from the frozen package's original selection only at Y3 QB developmental (D0 -> D1) and Y3 RB established (D0 -> D1), exactly as already implemented before this diagnostic.

## 7. Uncertainty actually carried into downstream value

The P0 runtime emits:
- discrete state probabilities;
- point conditional-state means;
- expected points.

It does **not** emit a within-state production draw, residual scale, or quantile function. Fitted package covariance/scale diagnostics are not used by the P0 scoring function.

The live P0 Intrinsic/Shapley path receives those state probabilities and point state means. Shapley computes a marginal value for each state mean and then probability-weights those values. Its Monte Carlo is over roster-order permutations, not over a conditional production distribution.

The regular-season NEXT-4 Simulation is a separate current-season path. It receives season forecast means, converts them to active-game means, and applies independently calibrated weekly volatility. Its code explicitly states that weekly volatility is not derived from season forecast uncertainty. The P0 dynasty Y2/Y3 state distribution is not sampled there.

## 8. Diagnostic response-curve construction

For every position x horizon x career-stage cell:
1. choose the current-source row nearest the cell median source points;
2. hold all non-target evidence fixed;
3. define the governed current central source range as cell P10 to P90;
4. sample 21 evenly spaced points;
5. emit two exact frozen-model curves:
   - `magnitude_only`: source points vary, source/state percentiles fixed;
   - `joint_evidence`: source points, source percentile, and state percentile vary continuously from cell P10 to P90.

The resulting 1,008 rows are persisted in `CONTINUOUS_EVIDENCE_RESPONSE_CURVES.csv`. These are structural sensitivity curves, not fitted challengers.

## 9. Interpretation rule

No percentage of a nonlinear total Forecast is claimed to be "owned" by a single input family. Where exact additive interpretation is invalid because probabilities are logistic, states mix nonlinearly, or the zero floor binds, the diagnostic reports:
- anchor-only sensitivity;
- full-minus-anchor differences;
- continuous response slopes;
- exact expected-value decompositions where algebraically valid.

That follows the directive's requirement not to force artificial percentage attribution.
