import json
import pytest

from fsffl.product.foundation4_cohort import align_foundation4_cohort
from fsffl.product.foundation4_shadow_inputs import (
    provide_foundation4_long_horizon_forecast_contract_for_rules,
    provide_foundation4_terminal_features,
    FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
)
from fsffl.state.models import LeagueRules


def _rules():
    return LeagueRules(team_count=12, roster_size=18, lineup=(),
        scoring=FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING)


def test_active_334_cohort_explicitly_excludes_inactive_reference_without_changing_baseline():
    reference = provide_foundation4_long_horizon_forecast_contract_for_rules(_rules())
    terminal = provide_foundation4_terminal_features()
    frozen_bytes = reference.model_dump_json(warnings=False)
    missing = 'sleeper:player:11199'
    active = set(terminal) - {missing}
    assert len(active) == 334
    aligned, tails = align_foundation4_cohort(player_ids=active,
        long_forecast=reference, terminal_features=terminal)
    assert {row.player_id for row in aligned.forecasts} == set(tails) == active
    assert json.loads(aligned.provenance['inactive_reference_ids']) == [missing]
    assert reference.model_dump_json(warnings=False) == frozen_bytes
    assert len(terminal) == 335
    unchanged, full_tails = align_foundation4_cohort(player_ids=set(terminal),
        long_forecast=reference, terminal_features=terminal)
    assert unchanged is reference
    assert full_tails == terminal


def test_active_cohort_rejects_missing_authority_instead_of_intersecting_it_away():
    reference = provide_foundation4_long_horizon_forecast_contract_for_rules(_rules())
    terminal = provide_foundation4_terminal_features()
    with pytest.raises(ValueError, match='lacks accepted component authority'):
        align_foundation4_cohort(player_ids=set(terminal) | {'unresolved-canonical-id'},
            long_forecast=reference, terminal_features=terminal)
