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
