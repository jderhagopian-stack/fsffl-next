"""Private derived States must not replace shared provider snapshot rows."""
from .contracts import ArtifactKey, ReusableArtifactRecord, canonical_fingerprint, utc_now
from fsffl.state.models import LeagueState


def account_rule_state_key(user_id: str, league_id: str, state_id: str) -> ArtifactKey:
    return ArtifactKey("account_rule_state", "account_league", canonical_fingerprint(user_id, league_id), state_id, "v1")


def persist_account_rule_state(store, *, user_id, league_state, payload):
    configuration = league_state.rule_configuration
    if configuration is None or configuration.mode != "saved":
        raise ValueError("Only saved personal rule States can be checkpointed.")
    expected_scope = canonical_fingerprint("account-league-rules-v1", user_id,
                                            league_state.league.league_id, league_state.league.season)
    if configuration.account_scope != expected_scope:
        raise ValueError("Cannot checkpoint another account's rule State.")
    store.put_immutable_artifact(ReusableArtifactRecord(
        key=account_rule_state_key(user_id, league_state.league.league_id, league_state.state_id),
        payload=payload, computed_at=utc_now(),
    ))


def restore_account_rule_state(store, *, user_id, league_id, state_id):
    row = store.get_reusable_artifact(account_rule_state_key(user_id, league_id, state_id))
    if row is None:
        return None
    state = LeagueState.model_validate(row.payload)
    if state.state_id != state_id or state.league.league_id != league_id:
        raise ValueError("Personal-rule State identity mismatch")
    if (state.rule_configuration is None or state.rule_configuration.mode != "saved" or
            state.rule_configuration.account_scope != canonical_fingerprint(
                "account-league-rules-v1", user_id, league_id, state.league.season)):
        raise ValueError("Personal-rule State account mismatch")
    return state
