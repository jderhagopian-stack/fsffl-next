# FUMBLES_LOST Annual Rollover Contract — 2027+

Date: 2026-09-29  
Status: **DETERMINISTIC REFRESH + MINIMAL ANNUAL GOVERNED FREEZE**

## Decision

A new broad Forecast study is **not** required every season.

The accepted model family and Week-2→17 rolling architecture remain fixed. Each target season requires one small governed refresh/freeze after the prior regular season's exact weekly data are finalized and before the new target season may claim first-party point authority.

This freeze is data/model-parameter governance, not model-family selection.

## Target-season refresh for season Y

Use only governed completed seasons through `Y-1`.

### 1. Exact source semantics

Require the same exact target:

`sack_fumbles_lost + rushing_fumbles_lost + receiving_fumbles_lost`.

Reject total fumbles or a changed/non-equivalent schema.

Persist source URLs, hashes, capture/build timestamps and the completed training-season list.

### 2. Position rates

Recompute, cumulatively through `Y-1`:
- lost fumbles / accepted opportunities by position;
- opportunity / game by position.

No named-player tuning and no position-specific calibration scalar.

### 3. Player role priors

Recompute player cumulative prior opportunity/game sufficient statistics through `Y-1`.

Retain the fixed **4 pseudo-game** role stabilizer.

### 4. Cutoff calibration

For every cutoff Week 2..17, recompute the same single global train-only ratio:

- pseudo-current seasons: 2022 through `Y-1`;
- each pseudo-current season uses only seasons strictly before itself for its historical rate/role inputs;
- current evidence is only Weeks 1..cutoff of that pseudo-current season;
- target is post-cutoff exact lost fumbles in the same season-equivalent shape.

No new family/router search is allowed.

### 5. Uncertainty

For each position and cutoff `c`:
- carry forward the previously frozen production floor at `c`;
- evaluate the newly completed season `Y-1` as an additional chronology-preserving held-out season at every cutoff;
- compute the **prefix maximum** of the new held-out residual RMSE through `c`;
- set:

`new_floor[p,c] = max(prior_floor[p,c], max(new_heldout_RMSE[p,k] for k <= c))`.

This preserves the already-frozen monotone cutoff invariant: a later, sparser remaining-season target may never receive a lower empirical floor merely because its same-cutoff RMSE happened to fall after an earlier spike.

Cold-start/identity-light retain the separate cold-start safety floor as applicable.

### 6. Materiality bounds

For cutoffs Week 0..17:
- carry forward the prior frozen fallback bound;
- compute the all-population position-wide historical maximum season-equivalent exact-lost-fumble target including the newly completed season;
- freeze the larger value.

This bound is independent of player identity and is used only for omission materiality, never as a point Forecast.

Re-evaluate the population coverage matrix. If an observed fallback population fails the 90% empirical gate, restrict that population/cutoff (prefer a conservative contiguous suffix when support is deteriorating) rather than inflating the bound after seeing the failure.

Identity-light eligibility follows the matching cold-start position/cutoff rule and additionally requires a known, non-conflicting canonical offensive position.

## Minimal annual freeze gate

Before target-season point authority can activate, persist a season-specific artifact containing:
- target season;
- exact source hashes/semantics;
- training seasons;
- position rates;
- position opportunity/game priors;
- player prior sufficient-statistics fingerprint;
- Week-2→17 calibration scalars;
- Week-2→17 uncertainty floors;
- Week-0→17 materiality bounds and population eligibility;
- model/uncertainty/materiality contract versions.

The freeze passes only if:
1. exact target semantics are available;
2. all scalars are finite/positive;
3. all uncertainty floors are finite/non-zero;
4. chronology/no-future-leakage checks pass;
5. the newly added held-out season does not violate the already-frozen rolling adequacy gates;
6. every materiality-eligible observed population meets the 90% coverage gate.

If any check fails, there is **no automatic point-authority promotion**. Keep `FUMBLES_LOST` explicitly omitted and use only a valid materiality allowance where a frozen bound/eligibility exists; otherwise fail closed and return the narrow evidence problem to Research/Management.

## Operational lifecycle

- Offseason/preseason / completed Week 0: explicit omission; materiality only.
- Completed Week 1: explicit omission; materiality only.
- Completed Week 2: point authority may activate from that target season's frozen table.
- Weeks 3-17: same rolling algorithm using the target-season table.
- Week 18: no new remaining-season rolling point estimate.
- After final season data are governed: generate the next target-season freeze.

## 2027 example

After finalized 2026 exact weekly data are available:
- target season = 2027;
- training history extends through 2026;
- pseudo-current calibration set extends through 2026;
- 2026 becomes the newest held-out contribution to uncertainty/materiality monitoring;
- one 2027 table is frozen before 2027 first-party point authority.

No 2027 numeric table can be honestly frozen on 2026-09-29 because the 2026 season is incomplete.
