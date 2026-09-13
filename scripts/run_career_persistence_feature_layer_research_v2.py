from __future__ import annotations

"""Superseding runner for the career-persistence study.

The first plumbing run proved the external feature join and workflow, but its
control calibration used a mean-of-ratios shortcut rather than FSFFL's governed
career calibration. That made its bounded control non-comparable to the prior
materializer study. This runner is the single permitted evidence-contract repair:
it reuses the exact governed empirical-Bayes calibration primitives and leaves the
predeclared feature selection, holdout seasons and acceptance gates unchanged.
"""

import math
import statistics

import run_career_calibration as rc
import run_career_persistence_feature_layer_research as study


class GovernedCalibration(study.Calibration):
    def __init__(self, training: list[study.Row], features: tuple[str, ...]):
        self.training = training
        self.features = features
        self.parent = {}
        self.cells = {}
        self.bounds = {}
        self.ceilings = {}
        self.scalers = {}
        self.prod_beta = {}
        self.surv_beta = {}

        converted = [
            rc.Row(
                player_id=r.player_id,
                season=r.season,
                position=r.position,
                current=r.current,
                nxt=r.nxt,
                survived=r.survived,
                age=r.age,
                experience=r.experience,
                rookie=r.experience == 0,
                production_quartile=min(4, max(1, int(r.percentile * 4) + 1)),
            )
            for r in training
        ]

        for pos in study.POSITIONS:
            rs = [r for r in training if r.position == pos]
            pos_converted = [r for r in converted if r.position == pos]
            fitted = rc.calibrate_position(pos_converted, pos)
            if not fitted:
                continue
            self.parent[pos] = self._from_governed(fitted[0])
            for item in fitted[1:]:
                if int(item["sample_size"]) < study.MIN_CELL_N or int(item["survivor_sample_size"]) < study.MIN_CELL_SURVIVORS:
                    continue
                age = item["age_years"] if item["age_years"] != "" else None
                key = (
                    pos,
                    age,
                    int(item["experience_years"]),
                    int(item["prior_production_quartile"]),
                    str(item["is_rookie_cohort"]).lower() == "true",
                )
                self.cells[key] = self._from_governed(item)

            survivor_ratios = [r.nxt / r.current for r in rs if r.survived and r.current > 0]
            self.bounds[pos] = (
                study.percentile(survivor_ratios, 0.05),
                study.percentile(survivor_ratios, 0.95),
            ) if survivor_ratios else (0.0, 2.0)
            self.ceilings[pos] = study.percentile([r.current for r in rs], 0.99)
            self._fit_enrichment(pos, rs)

    @staticmethod
    def _from_governed(item):
        return {
            "n": int(item["sample_size"]),
            "survivors": int(item["survivor_sample_size"]),
            "survival": float(item["survival_probability"]),
            "multiplier": float(item["conditional_production_multiplier"]),
            "dispersion": float(item["conditional_multiplier_stddev"]),
        }

    def evidence(self, row_or_state):
        pos = row_or_state.position
        q = min(4, max(1, int(row_or_state.percentile * 4) + 1))
        rookie = row_or_state.experience == 0
        key = (pos, row_or_state.age, row_or_state.experience, q, rookie)
        return self.cells.get(key, self.parent[pos])


# Preserve every frozen development/holdout choice and gate from the original
# study; replace only the control/evidence contract that was implemented
# inconsistently with existing FSFFL research.
study.Calibration = GovernedCalibration

if __name__ == "__main__":
    study.main()
