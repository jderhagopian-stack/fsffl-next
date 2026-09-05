from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path("artifacts/next2-career")
PANEL = ROOT / "career_transition_panel.csv"
EVIDENCE = ROOT / "career_transition_evidence.csv"
REPORT = ROOT / "career_calibration_report.md"
MODEL_VERSION = "next2-career-eb-v1"


@dataclass(frozen=True)
class Row:
    player_id: str
    season: int
    position: str
    current: float
    nxt: float
    survived: bool
    age: int | None
    experience: int
    rookie: bool
    production_quartile: int


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "t", "yes"}


def load_rows() -> list[Row]:
    rows: list[Row] = []
    with PANEL.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            percentile = float(raw["prior_production_percentile"])
            quartile = min(4, max(1, int(percentile * 4) + 1))
            age = int(raw["age_year_floor"]) if raw["age_year_floor"] else None
            rows.append(
                Row(
                    player_id=raw["player_id"],
                    season=int(raw["season"]),
                    position=raw["position"],
                    current=float(raw["fantasy_points"]),
                    nxt=float(raw["next_fantasy_points"]),
                    survived=parse_bool(raw["survived_next_season"]),
                    age=age,
                    experience=int(raw["experience_years"]),
                    rookie=parse_bool(raw["is_rookie_cohort"]),
                    production_quartile=quartile,
                )
            )
    return rows


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def sample_variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    center = mean(values)
    return sum((value - center) ** 2 for value in values) / (len(values) - 1)


def survival_prior(rows: list[Row]) -> tuple[float, float, float]:
    """Return empirical-Bayes alpha, beta and parent probability.

    Prior concentration is inferred from year-to-year survival-rate variation
    after subtracting expected binomial sampling noise. If no excess variation is
    detectable, the full parent sample size is used as the finite empirical
    concentration rather than inventing an external pseudo-count.
    """

    p = sum(row.survived for row in rows) / len(rows)
    by_year: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        by_year[row.season].append(row)
    rates = [sum(r.survived for r in year_rows) / len(year_rows) for year_rows in by_year.values()]
    observed = sample_variance(rates)
    sampling = mean([p * (1 - p) / len(year_rows) for year_rows in by_year.values()])
    excess = max(0.0, observed - sampling)
    if excess > 0 and 0 < p < 1:
        concentration = max(0.0, p * (1 - p) / excess - 1.0)
    else:
        concentration = float(len(rows))
    if concentration <= 0:
        concentration = 1.0
    return p * concentration, (1 - p) * concentration, p


def slope_stats(rows: list[Row]) -> tuple[float, float, float, int]:
    usable = [row for row in rows if row.survived and row.current > 0]
    if not usable:
        return math.nan, math.inf, math.nan, 0
    sum_x2 = sum(row.current**2 for row in usable)
    if sum_x2 <= 0:
        return math.nan, math.inf, math.nan, 0
    slope = sum(row.current * row.nxt for row in usable) / sum_x2
    residuals = [row.nxt - slope * row.current for row in usable]
    if len(usable) > 1:
        residual_variance = sum(value**2 for value in residuals) / (len(usable) - 1)
    else:
        residual_variance = math.nan
    slope_variance = residual_variance / sum_x2 if not math.isnan(residual_variance) else math.inf
    relative_dispersion = math.sqrt(sum(value**2 for value in residuals) / sum_x2)
    return max(0.0, slope), slope_variance, relative_dispersion, len(usable)


def production_prior_variance(rows: list[Row], parent_slope: float, parent_slope_variance: float) -> float:
    """Estimate real cohort-to-cohort slope variation beyond sampling error."""

    groups: dict[tuple[int | None, int, int, bool], list[Row]] = defaultdict(list)
    for row in rows:
        groups[(row.age, row.experience, row.production_quartile, row.rookie)].append(row)
    estimates: list[tuple[float, float]] = []
    for group_rows in groups.values():
        slope, variance, _, n = slope_stats(group_rows)
        if n and math.isfinite(variance):
            estimates.append((slope, variance))
    if len(estimates) < 2:
        return max(parent_slope_variance, 1e-12)
    raw_between = sample_variance([value for value, _ in estimates])
    sampling = mean([variance for _, variance in estimates])
    excess = max(0.0, raw_between - sampling)
    return max(excess, parent_slope_variance, 1e-12)


def calibrate_position(rows: list[Row], position: str) -> list[dict[str, object]]:
    pos_rows = [row for row in rows if row.position == position]
    if not pos_rows:
        return []
    evidence_through = max(row.season + 1 for row in pos_rows)
    alpha, beta, parent_survival = survival_prior(pos_rows)
    parent_slope, parent_slope_var, parent_dispersion, parent_survivors = slope_stats(pos_rows)
    if not math.isfinite(parent_slope_var):
        parent_slope_var = 0.0
    prior_slope_var = production_prior_variance(pos_rows, parent_slope, parent_slope_var)

    output: list[dict[str, object]] = []
    parent_survival_sd = math.sqrt(
        (alpha * beta) / (((alpha + beta) ** 2) * (alpha + beta + 1))
    ) if alpha > 0 and beta > 0 else 0.0
    output.append(
        {
            "position": position,
            "cohort_name": "position_all",
            "age_years": "",
            "experience_years": "",
            "is_rookie_cohort": "",
            "prior_production_quartile": "",
            "sample_size": len(pos_rows),
            "survivor_sample_size": parent_survivors,
            "conditional_production_multiplier": parent_slope,
            "survival_probability": parent_survival,
            "conditional_multiplier_stddev": parent_dispersion,
            "conditional_multiplier_standard_error": math.sqrt(parent_slope_var),
            "survival_standard_error": parent_survival_sd,
            "model_version": MODEL_VERSION,
            "evidence_through_season": evidence_through,
        }
    )

    cells: dict[tuple[int | None, int, int, bool], list[Row]] = defaultdict(list)
    for row in pos_rows:
        cells[(row.age, row.experience, row.production_quartile, row.rookie)].append(row)

    for (age, experience, quartile, rookie), cell_rows in sorted(
        cells.items(), key=lambda item: (item[0][0] if item[0][0] is not None else -1, item[0][1], item[0][2], item[0][3])
    ):
        successes = sum(row.survived for row in cell_rows)
        post_alpha = alpha + successes
        post_beta = beta + len(cell_rows) - successes
        survival = post_alpha / (post_alpha + post_beta)
        survival_sd = math.sqrt(
            (post_alpha * post_beta)
            / (((post_alpha + post_beta) ** 2) * (post_alpha + post_beta + 1))
        )

        cell_slope, cell_var, cell_dispersion, survivors = slope_stats(cell_rows)
        if not math.isfinite(cell_var):
            usable = [row for row in cell_rows if row.survived and row.current > 0]
            sum_x2 = sum(row.current**2 for row in usable)
            parent_residual_variance = parent_dispersion**2
            cell_var = parent_residual_variance / sum_x2 if sum_x2 > 0 else math.inf
        if survivors and math.isfinite(cell_slope) and math.isfinite(cell_var) and cell_var > 0:
            prior_precision = 1.0 / prior_slope_var
            cell_precision = 1.0 / cell_var
            multiplier = (parent_slope * prior_precision + cell_slope * cell_precision) / (prior_precision + cell_precision)
            multiplier_se = math.sqrt(1.0 / (prior_precision + cell_precision))
        elif survivors and math.isfinite(cell_slope) and cell_var == 0:
            multiplier = cell_slope
            multiplier_se = 0.0
        else:
            multiplier = parent_slope
            multiplier_se = math.sqrt(prior_slope_var)

        # Blend observed transition dispersion by survivor evidence. The parent
        # sample supplies the empirical fallback; no fixed aging-uncertainty
        # multiplier is introduced.
        if survivors > 1 and math.isfinite(cell_dispersion):
            dispersion = math.sqrt(
                (survivors * cell_dispersion**2 + parent_survivors * parent_dispersion**2)
                / (survivors + parent_survivors)
            )
        else:
            dispersion = parent_dispersion

        output.append(
            {
                "position": position,
                "cohort_name": f"age={age if age is not None else 'unknown'};exp={experience};q={quartile};rookie={str(rookie).lower()}",
                "age_years": "" if age is None else age,
                "experience_years": experience,
                "is_rookie_cohort": str(rookie).lower(),
                "prior_production_quartile": quartile,
                "sample_size": len(cell_rows),
                "survivor_sample_size": survivors,
                "conditional_production_multiplier": max(0.0, multiplier),
                "survival_probability": survival,
                "conditional_multiplier_stddev": dispersion,
                "conditional_multiplier_standard_error": multiplier_se,
                "survival_standard_error": survival_sd,
                "model_version": MODEL_VERSION,
                "evidence_through_season": evidence_through,
            }
        )
    return output


def main() -> None:
    rows = load_rows()
    if not rows:
        raise SystemExit("career transition panel is empty")
    positions = [position for position in ("QB", "RB", "WR", "TE") if any(row.position == position for row in rows)]
    evidence: list[dict[str, object]] = []
    for position in positions:
        evidence.extend(calibrate_position(rows, position))

    fieldnames = [
        "position", "cohort_name", "age_years", "experience_years", "is_rookie_cohort",
        "prior_production_quartile", "sample_size", "survivor_sample_size",
        "conditional_production_multiplier", "survival_probability",
        "conditional_multiplier_stddev", "conditional_multiplier_standard_error",
        "survival_standard_error", "model_version", "evidence_through_season",
    ]
    with EVIDENCE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(evidence)

    lines = [
        "# NEXT-2 Career Transition Calibration",
        "",
        "This research calibration estimates **football career transitions**, not dynasty value. It separates next-season survival/availability from conditional production change and keeps uncertainty attached to the evidence.",
        "",
        "## Method",
        "",
        "- Historical player-seasons are joined to the next season using stable player IDs.",
        "- Age is measured on September 1 of the forecast season, matching the preseason/full-season forecast use case.",
        "- Experience uses the player entry season when the identity source supplies one; otherwise the panel labels first observed statistical season as a fallback rather than hiding that limitation.",
        "- Prior production is represented by an empirical within-position/season quartile, so usage context enters without a manually chosen fantasy-point threshold.",
        "- Detailed cohorts use position + age + experience + production quartile + rookie status.",
        "- Sparse survival cells are shrunk toward a position prior whose strength is inferred from historical year-to-year variation after sampling noise.",
        "- Conditional production is a weighted through-origin next-vs-current production slope. This avoids unstable simple ratios for low-volume players.",
        "- Sparse production cells are precision-shrunk toward the position estimate using empirically estimated between-cohort variation.",
        "- No legacy aging curve or fixed age penalty is imported.",
        "",
        "## Position-level evidence",
        "",
        "| Position | Player-seasons | Survivors | Survival | Conditional production multiplier | Transition dispersion |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in evidence:
        if item["cohort_name"] != "position_all":
            continue
        lines.append(
            f"| {item['position']} | {item['sample_size']} | {item['survivor_sample_size']} | {float(item['survival_probability']):.3f} | {float(item['conditional_production_multiplier']):.3f} | {float(item['conditional_multiplier_stddev']):.3f} |"
        )
    rookie_counts = defaultdict(int)
    for row in rows:
        if row.rookie:
            rookie_counts[row.position] += 1
    lines.extend([
        "",
        "## Rookie evidence",
        "",
        "Rookies are explicitly tagged rather than being forced through a veteran curve. The detailed evidence file retains their age, experience=0, and prior-production context with the same empirical shrinkage rules.",
        "",
        "| Position | Rookie transition rows |",
        "| --- | ---: |",
    ])
    for position in positions:
        lines.append(f"| {position} | {rookie_counts[position]} |")
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- These estimates are forecast inputs only. They do not contain market price, dynasty value, roster fit, contender status, or transaction logic.",
        "- Small cohorts remain visibly uncertain and are shrunk; they are not promoted because a tiny sample produced an extreme curve.",
        "- The final-season transition is excluded until its next-season outcome exists, preventing partial/future outcome leakage.",
        "- Point-in-time player circumstances beyond age/experience/production require separate historical evidence and must not be backfilled from current knowledge.",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
