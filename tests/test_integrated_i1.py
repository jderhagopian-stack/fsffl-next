from __future__ import annotations

from fsffl.forecast.football_state import (
    CanonicalFootballStateEvidence,
    CanonicalRoleEvidence,
    ProviderStatusMapping,
    canonical_status_flags,
)
from fsffl.forecast.integrated_i1 import (
    I1_C,
    I1ForecastInput,
    I1TrainingRow,
    IntegratedI1Model,
    STATE_NAMES,
    age_band,
    feature_vector_for_validation,
)
from fsffl.state.models import Position


def _evidence(
    player_id: str,
    *,
    rich: bool,
    position: Position = Position.WR,
    role_band: str = "depth",
) -> CanonicalFootballStateEvidence:
    return CanonicalFootballStateEvidence(
        player_id=player_id,
        position=position,
        age_years=23,
        experience_years=2,
        current_fantasy_points=70,
        prior_fantasy_points=50,
        role=CanonicalRoleEvidence(games=16, opportunity_per_game=5, role_band=role_band),
        role_coverage=True,
        roster_weeks=17 if rich else 0,
        roster_coverage=rich,
        active_share=.8 if rich else 0,
        released_share=.05 if rich else 0,
        last_status_active=rich,
        last_status_attached=rich,
        status_change_count=1 if rich else 0,
        active_return_count=1 if rich else 0,
        participation_weeks=14 if rich else 0,
        stats_weeks=14 if rich else 0,
        snap_play_weeks=14 if rich else 0,
        participation_coverage=rich,
    )


def _rows() -> tuple[I1TrainingRow, ...]:
    rows = []
    states = list(STATE_NAMES)
    # 960 balanced synthetic rows ensure rich and reduced paths independently
    # clear the frozen I1 MINN=100 / MINC=15 gates for every threshold. Rich
    # membership varies by complete state-cycle block so it is independent of
    # the target-state residue itself.
    for index in range(960):
        target = states[index % len(states)]
        current = states[1 + (index % 5)]
        position = (Position.QB, Position.RB, Position.WR, Position.TE)[index % 4]
        points = float(20 + (index % 8) * 25)
        evidence = _evidence(
            str(index),
            rich=(index // len(states)) % 3 != 0,
            position=position,
        )
        rows.append(
            I1TrainingRow(
                position=position,
                age_band=age_band(position, 22 + index % 10),
                current_state=current,
                horizon=1 + index % 2,
                target_state=target,
                target_points=0 if target == "out" else float(10 + states.index(target) * 35),
                current_points=points,
                prior_points=max(0.0, points - 15),
                experience_years=index % 8,
                evidence=evidence,
            )
        )
    return tuple(rows)


def test_i1_c_is_frozen() -> None:
    assert I1_C == 0.25


def test_i1_probabilities_are_calibrated_coordinates_not_score() -> None:
    model = IntegratedI1Model(_rows())
    item = I1ForecastInput(
        position=Position.WR,
        age_band="young",
        current_state="usable",
        horizon=1,
        current_points=70,
        prior_points=50,
        experience_years=2,
        evidence=_evidence("test", rich=True),
    )
    result = model.predict(item)
    assert set(result.probabilities) == set(STATE_NAMES)
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-12
    assert abs(result.persistence_probability - (1 - result.probabilities["out"])) < 1e-12
    assert result.anticipated_points >= 0
    assert result.evidence_path == "rich"


def test_missing_roster_evidence_uses_reduced_path_not_inferred_death() -> None:
    model = IntegratedI1Model(_rows())
    item = I1ForecastInput(
        position=Position.WR,
        age_band="young",
        current_state="usable",
        horizon=2,
        current_points=70,
        prior_points=50,
        experience_years=2,
        evidence=_evidence("test", rich=False),
    )
    result = model.predict(item)
    assert result.evidence_path == "reduced"
    assert result.probabilities["out"] < 1.0


def test_provider_specific_codes_map_to_identical_canonical_features() -> None:
    a = ProviderStatusMapping(active_codes=frozenset({"ACT"}), attached_codes=frozenset({"ACT"}))
    b = ProviderStatusMapping(active_codes=frozenset({"ACTIVE"}), attached_codes=frozenset({"ACTIVE"}))
    assert canonical_status_flags("ACT", mapping=a) == canonical_status_flags("ACTIVE", mapping=b)

    first = I1ForecastInput(
        position=Position.WR,
        age_band="young",
        current_state="usable",
        horizon=1,
        current_points=70,
        prior_points=50,
        experience_years=2,
        evidence=_evidence("a", rich=True),
    )
    second = I1ForecastInput(
        position=Position.WR,
        age_band="young",
        current_state="usable",
        horizon=1,
        current_points=70,
        prior_points=50,
        experience_years=2,
        evidence=_evidence("b", rich=True),
    )
    assert feature_vector_for_validation(first, rich=True) == feature_vector_for_validation(second, rich=True)
