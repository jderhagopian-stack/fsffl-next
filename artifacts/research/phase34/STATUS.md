# FSFFL NEXT — Phase 3/4 Future-State Resolution Research Checkpoint

Checkpoint date: 2026-09-17
Authority: research only
Branch checkpoint target: `research/future-state-resolution-phase2`
Production authority: unchanged. PR #147 must not be modified, merged, deployed, or used to promote a challenger.

## 1. Completed Phase 3/4 work

The Phase 3/4 bounded protocol was frozen before challenger-result inspection in `artifacts/research/future_state_phase34_protocol.md`.

The preserved experiment harnesses are:

- `scripts/run_phase34_challenger_validation.py` — original year-by-year walk-forward harness. It was correct in intent but too slow for the execution window and repeatedly timed out before completing all standalone variants.
- `scripts/run_phase34_challenger_validation_fast.py` — blocked chronological harness created to preserve the same point-in-time discipline while reducing refits. It uses fixed folds: early 2014-2016 trained through 2013; mid 2017-2018 trained through 2016; validation 2019-2020 trained through 2018; holdout 2021-2022 trained through 2020. H1/H2 remain fit together; H3 remains direct/separate.

Completed standalone prediction outputs:

- The full local `part_age.csv` contains `baseline`, `A1`, and `A2` predictions: 46,512 rows total, 15,504 rows per variant, source seasons 2014-2022, all QB/RB/WR/TE, h=1/2/3.
- The full local `part_bcd.csv` contains standalone `B`, `C`, and `D` predictions: 46,512 rows total, 15,504 rows per variant on the same matched historical observations.
- The research-branch checkpoint persists all six standalone prediction arrays in `artifacts/research/phase34/phase34_standalone_checkpoint_f32.npz`: one shared 15,504-row key table plus float32 `p_out/depth/usable/starter/premium/elite` and `pred_points` arrays for baseline/A1/A2/B/C/D. Exact already-computed aggregate metrics are preserved separately in JSON; the original full local CSV SHA-256 hashes below identify the higher-precision source snapshots.

The A forms were predeclared as:

- A1: replace coarse persistence age-band one-hot with position-specific continuous exact-age terms.
- A2: A1 plus a QB late-age hinge above 37, RB/WR/TE late-age hinges above 31, and a young-TE hinge below 24.

A2 was selected over A1 **only on the 2019-2020 validation block** using persistence Brier then persistence log loss. Validation metrics:

- baseline persistence Brier `0.1768318163`, log loss `0.5256294314`;
- A1 persistence Brier `0.1740944028`, log loss `0.5187932697`;
- A2 persistence Brier `0.1739722251`, log loss `0.5186427395`.

The full already-computed aggregate baseline/A1/A2/B/C/D metrics for development, validation, and holdout are checkpointed in `artifacts/research/phase34/phase34_baseline_component_metrics.json`. The 2021-2022 holdout metrics were already calculated before this checkpoint request, but they were not used to choose A2.

Raw-file integrity at checkpoint:

- uncompressed `part_age.csv` SHA-256: `2d6af4ae7c288f6d6d73ddfd3a61adc8ab7d3f4f3040e6f8e2e946e9fcd9eece`
- uncompressed `part_bcd.csv` SHA-256: `c45e7acab7e313a37d2aec6ba514b33614bb717882dd767e66a642bc920eaac4`
- branch checkpoint `phase34_standalone_checkpoint_f32.npz` SHA-256: `a63b530c026cef7fbc64dc320488db151755211d3f429bbaf6cf9ba4022a6353`

## 2. Incomplete work

No combination challenger finished before checkpointing.

The exact interrupted calculation was the first combination batch:

```bash
python - <<'PY'
import sys
sys.path.insert(0,'/mnt/data/phase34_work')
import run_phase34_challenger_validation_fast as m
from pathlib import Path
E=m.build()
P=m.run_variants(E,['A2+B','A2+C'])
o=Path('/mnt/data/phase34_parts')
o.mkdir(exist_ok=True)
P.to_csv(o/'part_combo1.csv',index=False)
print('done',len(P))
PY
```

The process was interrupted before a completed `part_combo1.csv` was recoverable.

Still incomplete under the management directive:

- A2+B, A2+C, A2+D, and A2+B+C+D combination evaluation;
- position/stage/horizon subgroup interpretation beyond the already-computed aggregate checkpoint metrics;
- age-bin calibration summaries for A2;
- tail calibration summaries for D;
- C role-loss and conditional-production memory diagnostics from the fast harness;
- final historical component selection;
- governed 2026 sentinel decomposition;
- downstream Shapley/Intrinsic diagnostic;
- final Phase 3/4 management report.

## 3. Reusable artifacts/files

Repository checkpoint paths:

- `artifacts/research/future_state_phase34_protocol.md`
- `scripts/run_phase34_challenger_validation.py`
- `scripts/run_phase34_challenger_validation_fast.py`
- `artifacts/research/phase34/phase34_baseline_component_metrics.json`
- `artifacts/research/phase34/phase34_standalone_checkpoint_f32.npz`
- `artifacts/research/phase34/STATUS.md`

These reuse the already-authoritative Phase 2 point-in-time panel and corrected age/state residual methodology already present on this research branch. No Phase 1 or Phase 2 reconstruction is needed.

## 4. Blockers / composability discoveries

There is no research-design blocker. The interruption was execution/runtime related.

The standalone outputs are not all algebraically composable from the saved prediction CSVs:

- **A2 + D is mechanically composable at the probability-output level** from the saved tables because A changes persistence only, while D changes conditional positive-state probabilities only. A2 persistence can be combined with D's conditional positive-state distribution without inventing or retuning coefficients.
- **A2 + B cannot be reconstructed exactly from the saved prediction tables alone.** B changes state-conditioned production means through fold-fitted Bayesian-ridge carryover and state SDs. The final `pred_points` delta under baseline probabilities is insufficient to recover the exact A2-weighted production expectation. The frozen B fit/recalculation must be rerun, but no new model selection is required.
- **A2 + C requires refitting the frozen joint feature union.** A2 and C both enter the persistence logistic, and C also enters ordered positive-state models. Combining standalone probabilities after the fact is not equivalent to fitting the predeclared joint regularized model.
- **A2 + B + C + D requires the frozen joint A2/C/D probability fit plus the frozen B production recalculation.** This is a refit/re-execution of already-declared components, not a new challenger design.

Thus “mechanical union” in the frozen protocol means no new features, thresholds, supported cells, or coefficient choices after standalone results; it does **not** mean every combination can be formed by arithmetic on the completed CSVs.

## 5. Exact next executable step

Do not rerun baseline, A1, A2, B, C, or D. Reuse the checkpointed standalone outputs.

The first executable experiment after management authorizes continuation is the interrupted combination batch, using the frozen fast harness and existing Phase 2 evidence:

```bash
python - <<'PY'
import sys
sys.path.insert(0,'/mnt/data/phase34_work')
import run_phase34_challenger_validation_fast as m
from pathlib import Path
E=m.build()
P=m.run_variants(E,['A2+B','A2+C'])
o=Path('/mnt/data/phase34_parts')
o.mkdir(exist_ok=True)
P.to_csv(o/'part_combo1.csv',index=False)
print('done',len(P))
PY
```

After that, compute only the remaining predeclared combinations and diagnostics, then the sentinel report, then the management PDF. Do not modify PR #147, merge, deploy, or change production authority.

**CHECKPOINT STOP:** no further A/B/C/D experimentation was performed after this status file was prepared.

## 6. Phase 3/4 resume - A2+B completed

Resume branch: `research/future-state-resolution-phase34-resume`

Recovery checkpoint: `9494de9fd8cae596bec9382a0c5db4176c4b06f0`

Authorized and executed combination: `A2+B` only.

Execution identifiers:

- local research run: `a2b-only-20260917-recovery-01`;
- Phase 2 workflow run: `35196266697`;
- Phase 2 workflow head: `cbf723945e5442d654482fcfeb2a53cd7dc4b178`;
- Phase 2 artifact: `future-state-resolution-phase2-final`, artifact ID `10486530017`;
- Phase 2 artifact ZIP SHA-256: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`;
- governing fast-harness blob: `6906a11d8fbec7a62bc392b627963a393413a61e`;
- standalone comparison metrics blob: `3333092460a874e4413000c3448a99043779c430`.

Persisted A2+B artifacts:

- `artifacts/research/phase34/phase34_a2b_metrics.json` - overall, position, horizon, position-horizon, stage, and age/persistence calibration metrics; SHA-256 `8e4df6e356908fc0548ef518efbe5157b2038462c3da0e61007d425ca78f32d7`;
- `artifacts/research/phase34/phase34_a2b_prediction_checkpoint_f32.npz` - 15,504 compressed row-level predictions; SHA-256 `4add65267ed03bfacdadaa96ef11886732771466ba729f32cc0acf57166d7db0`.

The A2+B result commit is the commit containing this status update; its exact SHA is the branch head and is recorded in the execution report because a commit cannot embed its own SHA.

Exact next unexecuted stage: `A2+C`.

**RESUME STOP:** A2+C, A2+D, A2+B+C+D, named-player sentinels, Shapley/Intrinsic diagnostics, promotion, merge, and deployment remain unexecuted.

## 7. Phase 3/4 continuation - A2+D completed

Parent result commit: `71e06c47e2a4c2654deb711a11e8040ce9689aa7`

Authorized and executed combination: `A2+D` only.

Execution identifiers:

- local research run: `a2d-only-20260917-recovery-01`;
- Phase 2 workflow run: `35196266697`;
- Phase 2 workflow head: `cbf723945e5442d654482fcfeb2a53cd7dc4b178`;
- Phase 2 artifact: `future-state-resolution-phase2-final`, artifact ID `10486530017`;
- Phase 2 artifact ZIP SHA-256: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`;
- governing fast-harness blob: `6906a11d8fbec7a62bc392b627963a393413a61e`;
- frozen standalone comparison metrics blob: `3333092460a874e4413000c3448a99043779c430`;
- persisted A2+B metrics SHA-256: `8e4df6e356908fc0548ef518efbe5157b2038462c3da0e61007d425ca78f32d7`;
- persisted A2+B row checkpoint SHA-256: `4add65267ed03bfacdadaa96ef11886732771466ba729f32cc0acf57166d7db0`.

Persisted A2+D artifacts:

- `artifacts/research/phase34/phase34_a2d_metrics.json` - overall and subgroup metrics, frozen aggregate comparisons, age-bin persistence calibration, elite/premium tail calibration, and pairwise A2/A2+B deltas; SHA-256 `3c9da92e7bfc37e7fc2430a8db3564e76aafbf06e9c81d858d61c6eb1e15d79a`;
- `artifacts/research/phase34/phase34_a2d_prediction_checkpoint_f32.npz` - 15,504 compressed row-level predictions; SHA-256 `778b01c1d021a96eefa2fed7d75bae7c5a424fe40e755156d8f3a07834d0b703`.

The A2+D result commit is the commit containing this status update; its exact SHA is the branch head and is recorded in the execution report because a commit cannot embed its own SHA.

Exact next unexecuted step: management review and authorization decision among `A2+B+D`, deferring B, or proceeding to C.

**A2+D STOP:** A2+B+D, A2+C, A2+B+C+D, current-player sentinels, Shapley/Intrinsic diagnostics, promotion, merge, and deployment remain unexecuted.

## 8. Phase 3/4 continuation - A2+B+D completed

Parent result commit: `6e5271039fdf7c330914b6305b33ec9a854ff06b`

Authorized and executed combination: `A2+B+D` only.

Execution identifiers:

- local research run: `a2bd-only-20260917-recovery-01`;
- Phase 2 workflow run: `35196266697`;
- Phase 2 workflow head: `cbf723945e5442d654482fcfeb2a53cd7dc4b178`;
- Phase 2 artifact: `future-state-resolution-phase2-final`, artifact ID `10486530017`;
- Phase 2 artifact ZIP SHA-256: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`;
- governing fast-harness blob: `6906a11d8fbec7a62bc392b627963a393413a61e`;
- persisted A2+B metrics SHA-256: `8e4df6e356908fc0548ef518efbe5157b2038462c3da0e61007d425ca78f32d7`;
- persisted A2+B row checkpoint SHA-256: `4add65267ed03bfacdadaa96ef11886732771466ba729f32cc0acf57166d7db0`;
- persisted A2+D metrics SHA-256: `3c9da92e7bfc37e7fc2430a8db3564e76aafbf06e9c81d858d61c6eb1e15d79a`;
- persisted A2+D row checkpoint SHA-256: `778b01c1d021a96eefa2fed7d75bae7c5a424fe40e755156d8f3a07834d0b703`.

Persisted A2+B+D artifacts:

- `artifacts/research/phase34/phase34_a2bd_metrics.json` - aggregate and subgroup comparisons, A2+D and A2+B pairwise deltas, age persistence calibration, elite/premium tail calibration, and probability-identity verification; SHA-256 `ad65270afacb3f9f0b7b3a40c2164c33e4c27cf010c0c3e958218347fa4761bc`;
- `artifacts/research/phase34/phase34_a2bd_prediction_checkpoint_f32.npz` - 15,504 compressed row-level predictions; SHA-256 `6841fb0bb6406bbbf39a535e7708458eb91159236a301e00df2df4e36e7af103`.

The A2+B+D result commit is the commit containing this status update; its exact SHA is the branch head and is recorded in the execution report because a commit cannot embed its own SHA.

Exact next unexecuted step: management decision whether to test C or proceed to the current-player sentinel / downstream Intrinsic audit.

**A2+B+D STOP:** A2+C, A2+B+C+D, current-player sentinels, Shapley/Intrinsic diagnostics, promotion, merge, and deployment remain unexecuted.

## 9. Phase 3/4 final historical challenger - A2+C+D completed

Parent result commit: `4f1aad4589d80e0d2725d5a757d36254bbd21e36`

Authorized and executed combination: `A2+C+D` only. The frozen joint A2/C/D probability model was genuinely refit under the predeclared blocked chronology. B was not run or included.

Execution identifiers:

- local research run: `a2cd-only-20260917-final-challenger-01`;
- Phase 2 workflow run: `35196266697`;
- Phase 2 workflow head: `cbf723945e5442d654482fcfeb2a53cd7dc4b178`;
- Phase 2 artifact: `future-state-resolution-phase2-final`, artifact ID `10486530017`;
- Phase 2 artifact ZIP SHA-256: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`;
- governing fast-harness blob: `6906a11d8fbec7a62bc392b627963a393413a61e`;
- persisted A2+D metrics SHA-256: `3c9da92e7bfc37e7fc2430a8db3564e76aafbf06e9c81d858d61c6eb1e15d79a`;
- persisted A2+D row checkpoint SHA-256: `778b01c1d021a96eefa2fed7d75bae7c5a424fe40e755156d8f3a07834d0b703`;
- persisted A2+B+D metrics SHA-256: `ad65270afacb3f9f0b7b3a40c2164c33e4c27cf010c0c3e958218347fa4761bc`;
- persisted A2+B+D row checkpoint SHA-256: `6841fb0bb6406bbbf39a535e7708458eb91159236a301e00df2df4e36e7af103`.

Persisted A2+C+D artifacts:

- `artifacts/research/phase34/phase34_a2cd_metrics.json` - aggregate and subgroup comparisons, age-bin persistence calibration, elite/premium tail calibration, and frozen C role/production-memory diagnostics; SHA-256 `0f73a8ef168a0a52eb0a6f8b0ee66067f66c9ca24a9f0db13df77e2c00c63440`;
- `artifacts/research/phase34/phase34_a2cd_prediction_checkpoint_f32.npz` - 15,504 compressed row-level predictions; SHA-256 `7923cc45f91844f5e6e2a8580058e8d6f9f9e57e4b8799dade97ce22a4eedc94`.

C adds small but repeatable out-of-sample information on top of A2+D. Validation and holdout both improve persistence Brier/log loss, state Brier, overall points MAE, and active-player MAE. The frozen C role-loss and production-memory diagnostics also improve in both blocks. The main replicated gain is QB-centered; small subgroup regressions remain, and validation state log loss worsens slightly. Bias does not show a material holdout regression.

Historical challenger recommendation: `A2+C+D`. C earns inclusion; B remains deferred.

The A2+C+D result commit is the commit containing this status update; its exact SHA is the branch head and is reported after persistence because a commit cannot embed its own SHA.

Exact next unexecuted step: management sentinel review.

**A2+C+D STOP:** current-player sentinels, Shapley/Intrinsic diagnostics, production implementation, promotion, PR #147 changes, merge, and deployment remain unexecuted.

## 10. Fixed position-routing study completed

Parent result commit: `75d7474dbca20d7c5898b2687231e85b5a5c8135`

Authorized and executed routing only:

- QB -> persisted `A2+C+D` predictions;
- RB/WR/TE -> persisted `A2+D` predictions.

No model was refit, no alternative route was evaluated, and no current-player or downstream Intrinsic work was performed. All 15,504 rows matched one-to-one on `source_season`, `player_id`, `position`, and `horizon`; 1,911 QB rows and 13,593 non-QB rows were routed without drops or duplicates.

Execution identifier: `position-routing-20260917-fixed-qb-a2cd-01`.

Persisted routing-study artifacts:

- `artifacts/research/phase34/phase34_position_routing_metrics.json` - routed, universal A2+D, universal A2+C+D, and frozen-baseline comparisons with subgroup and calibration diagnostics; SHA-256 `e3bd9d1537cd6c078f465bcfaf297c58cda78a04b3bf67eae322d7e3753cd1cb`;
- `artifacts/research/phase34/phase34_position_routing_checkpoint_f32.npz` - 15,504 compressed routed row-level predictions; SHA-256 `e1c1c6f6e8ea337e24b18abf84be5fe429a7706df1dbf8be30f8316823337cb8`.

Decision-gate result: the fixed position-routing hypothesis earns further architectural consideration. Aggregate points MAE is essentially tied with universal A2+C+D while the route removes the repeated young RB, WR, and TE stage regressions in both validation and holdout. Active-player MAE improves slightly in both blocks. Probability and tail calibration changes are small and mixed, with no material new calibration harm. The route gives back some universal-C gains in older non-QB cohorts, so the evidence is corroborating rather than proof of a general routing architecture.

Recommended historical Forecast contender entering sentinel review: fixed position route `QB=A2+C+D; RB/WR/TE=A2+D`, with universal A2+C+D retained as the comparison benchmark.

The routing-study result commit is the commit containing this status update; its exact SHA is the branch head and is reported after persistence because a commit cannot embed its own SHA.

Exact next unexecuted step: management sentinel review.

**POSITION-ROUTING STOP:** no larger routing study, current-player sentinel, Shapley/Intrinsic diagnostic, production implementation, promotion, PR #147 change, merge, or deployment was performed.
