"""Small account/league/season settings using the existing bounded artifact store."""
from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime
from threading import RLock

from fsffl.state.account_rules import AccountRuleSettings, DraftOrderSettings, LeagueRuleChanges
from .contracts import ArtifactKey, PersistenceStore, ReusableArtifactRecord, canonical_fingerprint


class AccountRuleSettingsStore:
    def __init__(self, persistence: PersistenceStore | None = None):
        self.persistence = persistence
        self._cache: OrderedDict[str, AccountRuleSettings | None] = OrderedDict()
        self._lock = RLock()

    @staticmethod
    def scope(user_id: str, league_id: str, season: int) -> str:
        return canonical_fingerprint("account-league-rules-v1", user_id, league_id, season)

    @staticmethod
    def _key(scope: str, revision: str = "current") -> ArtifactKey:
        return ArtifactKey("account_league_rules", "account_league_season", scope, revision, "v1")

    def _remember(self, scope, settings):
        self._cache[scope] = settings
        self._cache.move_to_end(scope)
        while len(self._cache) > 128:
            self._cache.popitem(last=False)

    def get(self, user_id: str, league_id: str, season: int) -> AccountRuleSettings | None:
        scope = self.scope(user_id, league_id, season)
        with self._lock:
            if scope in self._cache:
                self._cache.move_to_end(scope)
                return self._cache[scope]
            row = self.persistence.get_reusable_artifact(self._key(scope)) if self.persistence else None
            settings = AccountRuleSettings.model_validate(row.payload) if row else None
            if settings and (settings.account_scope != scope or settings.league_id != league_id or settings.season != season):
                raise ValueError("Saved rules failed account/league/season identity verification.")
            self._remember(scope, settings)
            return settings

    def prepare(self, user_id: str, league_id: str, season: int, changes: LeagueRuleChanges,
                draft_order: DraftOrderSettings | None, *, saved_at: datetime | None = None,
                provider_rules=None) -> AccountRuleSettings:
        at = saved_at or datetime.now(UTC)
        scope = self.scope(user_id, league_id, season)
        revision = canonical_fingerprint(scope, changes.model_dump(mode="json"),
                                         draft_order.model_dump(mode="json") if draft_order else None, at.isoformat())
        return AccountRuleSettings(account_scope=scope, league_id=league_id, season=season,
                                   revision=revision, saved_at=at, changes=changes, draft_order=draft_order,
                                   provider_rules_at_save=provider_rules)

    def save(self, user_id: str, settings: AccountRuleSettings, *, expected_revision: str | None) -> None:
        scope = self.scope(user_id, settings.league_id, settings.season)
        if scope != settings.account_scope:
            raise ValueError("Cannot save another account's rules.")
        with self._lock:
            previous = self.get(user_id, settings.league_id, settings.season)
            if (previous.revision if previous else None) != expected_revision:
                raise ValueError("Rules changed in another window. Reload before saving.")
            if self.persistence:
                # Fail closed on save failure: no success response or in-memory
                # default that will mysteriously disappear after restart.
                self.persistence.put_immutable_artifact(ReusableArtifactRecord(
                    key=self._key(scope, settings.revision), payload=settings.model_dump(mode="json"),
                    computed_at=settings.saved_at,
                ))
                self.persistence.put_artifact(ReusableArtifactRecord(
                    key=self._key(scope), payload=settings.model_dump(mode="json"), computed_at=settings.saved_at,
                ))
            self._remember(scope, settings)
