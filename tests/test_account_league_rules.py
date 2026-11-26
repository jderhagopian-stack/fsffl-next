from datetime import UTC, datetime, timedelta
from dataclasses import replace
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from fsffl.persistence.account_rules import AccountRuleSettingsStore
from fsffl.persistence.session import persist_runtime_snapshot, restore_runtime_snapshot
from fsffl.product.runtime import PrivateBetaRuntimeStore, league_material_fingerprint, forecast_input_fingerprint
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.product.league_rules import build_rule_what_if, league_rules_payload
from fsffl.product.webapp import create_app, require_beta_user
from fsffl.state.account_rules import (
    DraftOrderSettings, LeagueRuleChanges, apply_account_rules, provider_rule_state,
)
from fsffl.state.models import (
    League, LeagueRules, LeagueState, LineupRequirement, ScoringRule, Team, TeamState,
    ProviderRef, RosterSlot, Provenance,
)
from fsffl.state.draft_order_policy import resolve_draft_order_policy
from fsffl.team_utility.future_pick import compile_supported_future_pick_policy


NOW = datetime(2026, 11, 26, 12, tzinfo=UTC)


class MemoryStore:
    def __init__(self):
        self.artifacts, self.leagues, self.users, self.teams = {}, {}, {}, {}
        self.writes = []
        self.fail = False

    def get_reusable_artifact(self, key):
        return self.artifacts.get(key)

    def put_artifact(self, row):
        if self.fail:
            raise RuntimeError("storage unavailable")
        self.writes.append(row.key)
        self.artifacts[row.key] = row

    def put_immutable_artifact(self, row):
        if row.key not in self.artifacts:
            self.put_artifact(row)
        return self.artifacts[row.key]

    def get_latest_reusable_artifact(self, **kwargs):
        rows = [row for row in self.artifacts.values()
                if all(getattr(row.key, key) == value for key, value in kwargs.items())]
        return max(rows, key=lambda row: row.computed_at) if rows else None

    def get_league_snapshot(self, *, provider, league_id, season):
        return self.leagues.get((provider, league_id, season))

    def put_league_snapshot(self, row):
        self.leagues[(row.provider, row.league_id, row.season)] = row

    def put_team_snapshot(self, row):
        self.teams[(row.provider, row.league_id, row.team_id)] = row

    def put_user_runtime_context(self, row):
        self.users[row.user_id] = row

    def get_user_runtime_context(self, *, user_id):
        return self.users.get(user_id)


@pytest.fixture
def state():
    return LeagueState(
        league=League(league_id="sleeper:rule-test", name="Rule Test", season=2026,
            provider_refs=(ProviderRef(provider="sleeper", external_id="rule-test"),),
            rules=LeagueRules(team_count=4, roster_size=12, ir_size=2,
                rookie_draft_rounds=3, playoff_team_count=2, playoff_start_week=16,
                fantasy_regular_season_end_week=15,
                lineup=(LineupRequirement(slot="QB", count=1), LineupRequirement(slot="WR", count=2)),
                scoring=(ScoringRule(stat="rec", points=1),))),
        as_of=NOW - timedelta(days=1),
        teams=tuple(Team(team_id=str(i), league_id="sleeper:rule-test", display_name=f"Team {i}") for i in range(4)),
        team_states=tuple(TeamState(team_id=str(i), roster=(), max_points_for=100+i, max_points_for_provenance=Provenance(source="sleeper", retrieved_at=NOW-timedelta(days=1), effective_at=NOW-timedelta(days=1))) for i in range(4)),
        players=(), player_states=(),
    )


def candidate(repo, state, *, user="alice", changes=None, draft=None):
    return repo.prepare(user, state.league.league_id, state.league.season,
        changes or LeagueRuleChanges(ir_size=3), draft, saved_at=NOW, provider_rules=state.league.rules)


def client_for(state, memory=None):
    store = PrivateBetaRuntimeStore()
    store.set_league_state("alice", state)
    app = create_app(runtime_store=store, persistence_store=memory)
    app.dependency_overrides[require_beta_user] = lambda: "alice"
    return TestClient(app), store, app


def test_provider_identity_is_unchanged_and_reset_is_exact(state):
    repo = AccountRuleSettingsStore()
    assert apply_account_rules(state, None) is state
    assert '"rule_configuration"' not in state.canonical_json()
    changed = apply_account_rules(state, candidate(repo, state))
    assert changed.state_id != state.state_id
    assert provider_rule_state(changed).state_id == state.state_id
    assert changed.team_states == state.team_states
    assert changed.as_of == NOW
    assert changed.rule_configuration.provider_as_of == state.as_of


def test_personal_settings_are_account_and_season_scoped_and_survive_restart(state):
    db = MemoryStore()
    repo = AccountRuleSettingsStore(db)
    chosen = candidate(repo, state)
    repo.save("alice", chosen, expected_revision=None)
    cold = AccountRuleSettingsStore(db)
    assert cold.get("alice", state.league.league_id, 2026) == chosen
    assert cold.get("bob", state.league.league_id, 2026) is None
    assert cold.get("alice", state.league.league_id, 2027) is None
    with pytest.raises(ValueError, match="another account"):
        cold.save("bob", chosen, expected_revision=None)
    with pytest.raises(ValueError, match="another window"):
        repo.save("alice", chosen, expected_revision=None)
    assert len(db.artifacts) == 2


def test_refresh_uses_new_provider_facts_and_keeps_override_and_conflict(state):
    repo = AccountRuleSettingsStore()
    chosen = candidate(repo, state)
    repo.save("alice", chosen, expected_revision=None)
    store = PrivateBetaRuntimeStore()
    store.account_rule_settings = repo
    updated = state.model_copy(update={"as_of": NOW+timedelta(hours=1), "league":state.league.model_copy(
        update={"rules":state.league.rules.model_copy(update={"ir_size":4, "taxi_size":2})})})
    personal = store.prepare_account_league_state("alice", updated)
    assert personal.league.rules.ir_size == 3
    assert personal.league.rules.taxi_size == 2
    store.set_league_state("alice", personal)
    assert league_rules_payload(store.get("alice"), repo, "alice")["provider_conflicts"] == ["ir_size"]
    assert store.prepare_account_league_state("bob", personal).state_id == updated.state_id
    assert store.prepare_account_league_state("alice", personal).state_id == personal.state_id


@pytest.mark.parametrize("draft", [
    DraftOrderSettings(non_playoff_order="max_pf", playoff_order="elimination", tiebreak="record"),
    DraftOrderSettings(non_playoff_order="custom", playoff_order="custom", tiebreak="custom", notes="Lottery"),
])
def test_unsupported_rule_is_saved_as_explicit_and_never_record_fallback(state, draft):
    repo = AccountRuleSettingsStore()
    changed = apply_account_rules(state, candidate(repo, state, draft=draft))
    policy = resolve_draft_order_policy(changed.draft_order_policies, league_id=state.league.league_id,
        draft_season=2027, as_of=changed.as_of)
    assert policy is not None
    with pytest.raises(ValueError, match="unsupported explicit"):
        compile_supported_future_pick_policy(policy, draft_season=2027, team_count=4, playoff_team_count=2)


def test_supported_rule_reaches_existing_compiler_and_does_not_rescore_players(state):
    draft = DraftOrderSettings(non_playoff_order="record", playoff_order="elimination", tiebreak="record_h2h_points_for")
    changed = apply_account_rules(state, candidate(AccountRuleSettingsStore(), state, draft=draft))
    compiled = compile_supported_future_pick_policy(changed.draft_order_policies[0], draft_season=2027,
        team_count=4, playoff_team_count=2)
    assert compiled.authority == "explicit_league_rule"
    assert forecast_input_fingerprint(changed) == forecast_input_fingerprint(state)
    assert league_material_fingerprint(changed) != league_material_fingerprint(state)


def test_configuration_never_rewrites_earlier_snapshot_or_backdates_rule(state):
    changed = apply_account_rules(state, candidate(AccountRuleSettingsStore(), state,
        draft=DraftOrderSettings(non_playoff_order="max_pf", playoff_order="elimination", tiebreak="unresolved")))
    assert resolve_draft_order_policy(changed.draft_order_policies, league_id=state.league.league_id,
        draft_season=2027, as_of=state.as_of) is None
    assert not state.draft_order_policies


def test_private_state_durability_never_overwrites_provider_snapshot(state):
    db = MemoryStore()
    persist_runtime_snapshot(db, user_id="bob", league_state=state, selected_team_id=None)
    original = dict(db.leagues)
    repo = AccountRuleSettingsStore(db)
    personal = apply_account_rules(state, candidate(repo, state))
    persist_runtime_snapshot(db, user_id="alice", league_state=personal, selected_team_id=None)
    assert db.leagues == original
    assert restore_runtime_snapshot(db, user_id="alice").league_state.state_id == personal.state_id
    assert restore_runtime_snapshot(db, user_id="bob").league_state.state_id == state.state_id


def test_durable_runtime_restores_account_settings_and_exact_state(state):
    db = MemoryStore()
    repo = AccountRuleSettingsStore(db)
    chosen = candidate(repo, state)
    repo.save("alice", chosen, expected_revision=None)
    personal = apply_account_rules(state, chosen)
    persist_runtime_snapshot(db, user_id="alice", league_state=personal, selected_team_id="1")
    runtime = PersistentPrivateBetaRuntimeStore(db)
    context = runtime.restore_user("alice")
    assert context.league_state.state_id == personal.state_id
    assert context.selected_team_id == "1"
    assert runtime.prepare_account_league_state("alice", state).state_id == personal.state_id


def test_restart_recovers_crash_between_settings_commit_and_state_activation(state):
    db = MemoryStore()
    persist_runtime_snapshot(db, user_id="alice", league_state=state, selected_team_id="1")
    repo = AccountRuleSettingsStore(db)
    chosen = candidate(repo, state)
    repo.save("alice", chosen, expected_revision=None)
    runtime = PersistentPrivateBetaRuntimeStore(db)
    context = runtime.restore_user("alice")
    assert context.league_state.league.rules.ir_size == 3
    assert context.selected_team_id == "1"
    assert context.simulation_analytics is None and context.publication_generation_id is None
    assert runtime.wait_for_checkpoint("alice")


def test_api_save_refresh_reset_and_cross_account_isolation(state):
    db = MemoryStore()
    client, store, app = client_for(state, db)
    old = client.get("/api/league/rules").json()
    assert old["provider_rules"]["ir_size"] == 2
    assert old["draft_order_confirmed"] is False
    saved = client.post("/api/league/rules", json={"expected_state_id": old["state_id"], "changes":{"ir_size":3}})
    assert saved.status_code == 200, saved.text
    data = saved.json()
    assert data["effective_rules"]["ir_size"] == 3 and data["durable"]
    assert store.prepare_account_league_state("alice", state).league.rules.ir_size == 3
    app.dependency_overrides[require_beta_user] = lambda: "bob"
    store.set_league_state("bob", state)
    assert client.get("/api/league/rules").json()["effective_rules"]["ir_size"] == 2
    assert client.post("/api/league/rules", json={"expected_state_id":data["state_id"], "changes":{"ir_size":5}}).status_code == 409
    app.dependency_overrides[require_beta_user] = lambda: "alice"
    assert client.post("/api/league/rules", json={"expected_state_id":old["state_id"], "changes":{}}).status_code == 409
    assert client.post("/api/league/rules", json={"expected_state_id":data["state_id"], "changes":{}}).status_code == 409
    reset = client.post("/api/league/rules/reset", json={"expected_state_id":data["state_id"], "expected_revision":data["revision"]})
    assert reset.status_code == 200, reset.text
    assert reset.json()["state_id"] == state.state_id
    assert not reset.json()["has_overrides"]


def test_failed_save_is_not_activated_or_reported_as_saved(state):
    db = MemoryStore()
    client, store, _ = client_for(state, db)
    client.get("/api/league/rules")
    db.fail = True
    response = client.post("/api/league/rules", json={"expected_state_id":state.state_id,"changes":{"ir_size":3}})
    assert response.status_code == 503
    assert store.get("alice").league_state.state_id == state.state_id
    assert store.account_rule_settings.get("alice", state.league.league_id, 2026) is None


@pytest.mark.parametrize("changes", [
    {"roster_size":2}, {"ir_size":-1}, {"playoff_team_count":3}, {"playoff_team_count":8},
    {"lineup":[{"slot":"BENCH","count":1000}]},
    {"lineup":[{"slot":"QB","count":1},{"slot":"QB","count":2}]},
    {"scoring":[{"stat":"rec","points":1},{"stat":"rec","points":2}]},
    {"team_count":12},
])
def test_invalid_rule_changes_do_not_activate(state, changes):
    client, store, _ = client_for(state)
    result = client.post("/api/league/rules", json={"expected_state_id":state.state_id,"changes":changes})
    assert result.status_code == 422
    assert store.get("alice").league_state.state_id == state.state_id


def test_preview_is_unsaved_and_draft_only_does_not_spend_simulation(state):
    client, store, _ = client_for(state, MemoryStore())
    old = deepcopy(store.get("alice"))
    result = client.post("/api/league/rules/preview", json={"expected_state_id":state.state_id,
        "draft_order":{"non_playoff_order":"max_pf","playoff_order":"elimination","tiebreak":"record"}})
    assert result.status_code == 200, result.text
    assert result.json()["saved"] is False and result.json()["draft_order_supported"] is False
    assert store.get("alice") == old
    assert store.account_rule_settings.get("alice", state.league.league_id, 2026) is None


def test_what_if_without_baseline_does_not_invent_competitive_results(state):
    client, store, _ = client_for(state)
    result = client.post("/api/league/rules/preview", json={"expected_state_id":state.state_id,
        "changes":{"scoring":[{"stat":"rec","points":0.5}]}})
    assert result.status_code == 200
    assert result.json()["teams"] == []
    assert "Run your league analysis" in result.json()["message"]
    assert store.get("alice").league_state.state_id == state.state_id
