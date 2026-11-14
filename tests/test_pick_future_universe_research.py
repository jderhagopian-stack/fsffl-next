"""Research integration requirement: equal units do not establish equal games."""
import pytest

from fsffl.state.models import LeagueRules, LineupRequirement, RosterSlot
from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS, FROZEN_SHAPLEY_SEED,
    monte_carlo_shapley_scenarios, subset_caps_from_rules,
)


def test_new_entrant_value_cannot_be_added_to_incumbents_from_a_different_population():
    rules=LeagueRules(team_count=2,roster_size=3,
        lineup=(LineupRequirement(slot=RosterSlot.QB,count=1),),scoring=())
    caps=subset_caps_from_rules(rules)
    def values(players):
        result=monte_carlo_shapley_scenarios(players,{pid:(points,) for pid,_,points in players},caps,
            permutations=FROZEN_SHAPLEY_PERMUTATIONS,seed=FROZEN_SHAPLEY_SEED)
        return {pid:row[0] for pid,row in result.estimates.items()}
    base=values([('incumbent','QB',100),('backup','QB',50)])
    expanded=values([('incumbent','QB',100),('backup','QB',50),('future-entrant','QB',100)])
    assert sum(base.values())==pytest.approx(150)
    assert sum(expanded.values())==pytest.approx(200)
    assert sum(base.values())+expanded['future-entrant']>200
    assert expanded['incumbent']<base['incumbent']
    assert expanded['backup']<base['backup']
