# Long-Term Intrinsic Consumption Contract — Frozen Before Validation

Date: 2026-09-27  
State: **FROZEN BEFORE CONSUMER VALIDATION / RESEARCH ONLY**

## Purpose

Define a separate Value-layer **Long-Term Intrinsic** for the governed Y4-Y7 Forecast trajectory without replacing, blending into, or modifying Current Intrinsic (Y1-Y3).

This contract consumes Forecast. It does not select Forecast.

Production Forecast, Current Intrinsic, Market, Decision and Team Utility remain unchanged.

## Economic target

Long-Term Intrinsic measures:

> **the player's expected annual marginal lineup capacity over the governed Y4-Y7 window in the connected league economy.**

The economic primitive remains the same league-aware Shapley deployment game used by Current Intrinsic:
- actual league lineup capacities;
- QB/RB/WR/TE eligibility;
- FLEX and SUPERFLEX competition;
- no Market input;
- no owner preference;
- no team-specific competitive window;
- no named-player adjustment.

For each target year h in {4,5,6,7}, Forecast supplies a governed distribution / policy set. Value computes that year's expected Shapley marginal lineup contribution, `phi_h`.

The raw long-term quantity is:

`LT_RAW = (phi_4 + phi_5 + phi_6 + phi_7) / 4`

This is an **equivalent annual marginal-lineup-capacity rate**, not a cumulative lifetime sum.

### Why divide by four

The four years are the complete Management-authorized precise long-term window. Each is one NFL season. Summing and dividing by the number of seasons is a unit normalization from four-season total marginal capacity to one-season-equivalent marginal capacity.

It is **not** an arbitrary horizon-weight vector:
- every governed season has coefficient 1 before unit normalization;
- Y4 is not skipped;
- H5 is not privileged;
- no recency discount is introduced;
- no dynasty preference is embedded.

A discounted Y4-Y7 present value is **not** Intrinsic authority because choosing a long-horizon discount rate would encode time preference / competitive-window preference that belongs downstream unless independently economically validated.

## Forecast input authority

### Exact-policy cells
Use the exact Research-authorized policy only:
- QB Y5: `blanket_75_25`;
- WR Y5: `hard_router`.

### Set-valued cells
For every other Y4-Y7 position×horizon cell, preserve the exact symmetric authority set from:
`artifacts/research/y4_y8_symmetric_authority_20260927/Y4_Y8_CELL_AUTHORITY_MAP.csv`.

Do not silently choose baseline, soft stack, hard router or 75/25 inside an unresolved cell.

For a player, Value therefore receives for each year:
- one exact annual Forecast where exact authority exists; or
- a supported set of annual Forecast alternatives.

## Long-Term Intrinsic authority representation

### Exact / central raw
When every annual input is exact, `LT_RAW` is a scalar.

### Model-authority envelope
When one or more annual inputs are set-valued, the authoritative Long-Term Intrinsic is a **set/envelope**, not a secretly selected model.

For each horizon:
- compute expected annual Shapley under every supported Forecast policy;
- retain the annual minimum and maximum expected Shapley.

Then:
- `LT_AUTHORITY_LOW = mean(annual minima Y4-Y7)`;
- `LT_AUTHORITY_HIGH = mean(annual maxima Y4-Y7)`.

Because the consumer is additive with equal season units, these bounds are the exact rectangular-envelope bounds implied by the supported annual authority sets.

A display midpoint may be reported mechanically as `(LOW+HIGH)/2`, but:
- it is not a selected Forecast;
- it is not a posterior mean;
- it cannot be used to claim model authority.

## Within-model Forecast uncertainty

Within-model uncertainty remains distinct from model-authority uncertainty.

For each policy/year preserve:
- central Forecast;
- 80% and 90% annual residual/conformal uncertainty where governed;
- annual expected Shapley under the central forecast;
- Shapley of the annual low/high scenarios or equivalent scenario propagation.

Do **not** combine annual variances as independent.

For Y4-Y7 aggregate uncertainty report:
1. per-horizon within-model uncertainty;
2. a deterministic interval-arithmetic long-term band obtained by averaging annual low bounds and annual high bounds for a fixed policy path;
3. optionally an RSS sensitivity proxy only if explicitly labeled non-authoritative;
4. a perfect-positive-covariance upper-envelope sensitivity if a variance form is available.

No exact cumulative long-term SD is authorized because cross-horizon covariance remains unvalidated.

## Y8

Y8 is excluded from precise Long-Term Intrinsic.

It may appear only as:
- coarse persistence/context;
- an uncertainty annotation;
- a separate research terminal lens.

It contributes zero cardinal weight to Long-Term Intrinsic under this contract.

## Current Intrinsic relationship

Current Intrinsic remains:
- separate;
- Y1-Y3;
- governed by the current three-year Shapley contract;
- a discounted cumulative near/medium-term quantity.

Long-Term Intrinsic is:
- Y4-Y7;
- an equivalent annual marginal-capacity rate;
- undiscounted inside its fixed window;
- often set-valued because Forecast authority is set-valued.

The two raw quantities are **not additive** and should never be summed into a master player number.

A player may legitimately have:
- high Current / high Long-Term;
- high Current / low Long-Term;
- low Current / high Long-Term;
- low Current / low Long-Term.

That disagreement is information, not an error to be averaged away.

## Historical validation plan — frozen before scoring

Use exact prior rolling PIT predictions:
- 11,940 unique player-origin rows;
- Y4-Y7 only for cardinal Long-Term Intrinsic validation;
- exact common keys;
- policies baseline / hard_router / soft_stack / blanket_75_25;
- actual realized target fantasy points;
- connected-league lineup contract.

For each outer base season and target horizon:
1. compute horizon-specific Shapley from each policy's predicted fantasy points;
2. compute realized horizon-specific Shapley from actual fantasy points on the same player universe;
3. retain only player-origin observations with all Y4-Y7 horizons available for the four-season consumer validation;
4. compute predicted `LT_RAW` for each frozen policy;
5. compute realized `LT_RAW` as the mean realized annual Shapley across Y4-Y7.

Validate:
- MAE / RMSE / bias;
- Spearman;
- top-tail error;
- origin stability;
- position and career-stage discrimination where recoverable;
- monotonicity of the consumer in annual Shapley inputs;
- efficiency/reconciliation of the underlying Shapley game.

### Falsification comparators
Without tuning:
- H5-only annual Shapley snapshot;
- H7-only annual Shapley snapshot;
- mean Y4-Y7 raw expected fantasy points.

The single-horizon comparators test whether the continuous window contains useful information beyond a headline or terminal shortcut. Raw points are rank-only/context because they omit league scarcity economics.

This is a **historical comparative replay**, not a pristine new final holdout: the Forecast policies were previously studied. It validates the Value consumer, not new Forecast selection.

## Current 335-player PIT shadow

After the economic contract above is frozen:
- compute Long-Term Intrinsic from the already-frozen 335-player Y4-Y7 shadows;
- compare with the read-only Current Intrinsic reference;
- report distribution, position, age/career-stage and rank disagreement;
- do not tune the consumer from named players.

## Product scale

### Raw authority
Always retain `LT_RAW` and authority bounds in native Shapley marginal-fantasy-point units.

### 0-10,000 display ruler
Long-Term Intrinsic may use a **separate 0-10,000 rank-calibrated display index** if validation passes.

Proposed semantics:
- scale id: `fsffl-long-term-intrinsic-index`;
- 0-10,000 is a monotone within-lens standing ruler;
- fixed reference cohort and quantile knots must be versioned;
- 8,000 on Long-Term Intrinsic means roughly the same *standing within the Long-Term lens* as 8,000 on another rank-calibrated lens, not the same additive raw economic magnitude.

The display index must never be summed with Current Intrinsic or Market Cardinal.

If a historically stable reference calibration cannot be frozen, production must expose raw + percentile until it can.

## Downstream containment

### Market
Market may compare:
- Broad/League Market;
- Current Intrinsic;
- Long-Term Intrinsic;
as separate coordinates.

A Market opportunity may describe near-term-vs-durable disagreement but may not collapse them into acceptance probability or one hidden value.

### Team Utility
Team Utility may consume Current and Long-Term Intrinsic as separate vector inputs. A contender/rebuilder policy may weight them **downstream** only under a separately governed competitive-window utility contract.

Those weights are not player Intrinsic.

### Trade / Decision
Decision may expose whether a package exchanges Current for Long-Term value, but bilateral recommendation/acceptance remains Decision authority.

## Promotion gates for this Research directive

The consumer is supportable only if:
- horizon-specific Shapley is deterministic and economically reconciled;
- four-year mean is monotone in each annual Shapley coordinate;
- PIT replay shows useful discrimination against realized long-term marginal lineup capacity;
- continuous Y4-Y7 is not materially inferior to a single-horizon shortcut on the target it claims to represent;
- set-valued authority is preserved rather than collapsed;
- scale semantics remain separate/non-additive;
- uncertainty layers remain separate;
- no Y8 cardinal contribution is introduced.

No production deployment is authorized by passing these Research gates.
