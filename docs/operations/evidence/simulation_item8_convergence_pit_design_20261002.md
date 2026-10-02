# Simulation 2.0 item 8 — convergence + PIT calibration evidence plan

**Status:** preserved pre-result evidence design. The study is complete; final interpretation is recorded in `simulation_item8_convergence_results_20261002.md`. No production-authority change is authorized by this document.

## Production authority lock

Canonical current-State Simulation remains **50,000 runs**. The item-7 preview counts (1,000 screening and 5,000 provisional) are not evidence for reducing canonical authority. No adaptive trial-count rule may be promoted from this study without a separate Management sanity check and explicit approval.

## Convergence study

The executable harness is `scripts/run_simulation_convergence_pit_study.py`.

It uses the production NumPy/PCG64 batched protocol (batch 500) on one governed 12-team / 14-week / six-playoff-team fixture with:
- configured standard playoff weeks 15-17;
- next-season origin-team pick distributions under the governed standard draft-order fallback;
- one clear common-world competitive scenario (+6 / -6 weekly points for two teams);
- one near-boundary common-world scenario (+0.5 / -0.5 weekly points).

Executed counts: **1k, 5k, 10k, 25k, 35k, 50k, 75k, 100k**. The **1k** row is item-7 screening context only; the governed convergence study range remains **5k-100k**.

Independent roots: **8**. Each lower count is compared with the same-root 100k output. The 100k output is a study reference only; it does not become authority.

Reported convergence dimensions:
- max per-team expected-wins absolute deviation;
- max per-team playoff and championship probability deviation;
- max per-team regular-season finish-distribution total-variation distance;
- max origin-team future-pick-slot distribution total-variation distance;
- clear and near-boundary common-world scenario-delta error for expected wins, playoff probability and championship probability;
- sign agreement of those scenario deltas with the same-root 100k result;
- runtime for the three-run bundle at each count.

No single numeric margin in this study is itself a promotion rule. Interpretation should distinguish:
1. numerical convergence;
2. practical product materiality;
3. decision/sign stability;
4. runtime benefit.

Any proposed authority-count change returns to Management before code/config promotion.

## PIT calibration rule

Historical calibration must use only inputs actually knowable at the historical cutoff.

Eligible full-Simulation PIT case requires:
1. a timestamped historical canonical League State;
2. historical Forecast evidence with `effective_at / available_at <= cutoff`;
3. the governed historical league rules needed by the simulated output;
4. realized fantasy outcomes after the cutoff;
5. no current roster, current Forecast, current market data or later provider revision in the input path.

The original repo-only precheck was insufficient because production durability is in Supabase rather than Render Postgres. A read-only audit of the connected **FSFFL NEXT** Supabase project found authentic 2026 PIT evidence: **364 canonical State snapshots**, **12 immutable provider projection snapshots / 22,050 normalized observations**, **6 prospective football-state captures**, and hundreds of State-scoped current-Forecast artifacts. The bounded audit also found authentic pre-opener offense Forecast artifact **63** at **2026-09-09T23:26:16.657633Z**, but no retained matching canonical State payload, so it is Forecast-only evidence rather than a full calibration checkpoint. The earliest exact retained State+Forecast pair is post-opener: State `a7d56f...` at **2026-09-10T12:44:36.198236Z** with Forecast artifact **87** at **12:45:33.703488Z**. Artifact **145** is also post-opener and must not be labeled preseason PIT evidence.

That evidence proves genuine prospective calibration inputs exist. It does **not** yet create a finalized season-end calibration cohort: the 2026 season is still active, so final wins/finish/playoff/title/2027 pick-slot outcomes are not yet realized. Item 8 therefore records **0 fully realized final-season Simulation calibration cases now**, retains the authentic checkpoints for prospective scoring, and must not manufacture historical outcomes or Forecasts. The sanitized audit is retained in `docs/operations/evidence/simulation_item8_pit_inventory_20261002.json` and the reusable leakage guards/scoring framework lives in `fsffl.team_utility.simulation_validation`.

## Decision rule for this turn

Run and retain the full convergence evidence, including independent-root dispersion and scenario-delta sign sensitivity. Verify the PIT framework against the authentic inventory and report finalized sample size separately from available prospective checkpoints. Keep 50,000 unchanged.

If convergence evidence suggests a materially defensible lower/higher count, return the proposed count/rule and evidence to Management for sanity check. Do not implement it first.

### Bounded evidence-stop rule

The authenticated Supabase/repo inventory above is the item-8 evidence set. Per Management's no-hunt rule, implementation does not scrape, reconstruct, infer, or broaden into an archive search for older Forecasts. Missing pre-2026 full-league Forecast coverage is recorded as a limitation, not a blocker.
