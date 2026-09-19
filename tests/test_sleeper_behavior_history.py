from fsffl.behavioral.models import BehavioralAssetKind, BehavioralEventKind
from fsffl.behavioral.sleeper_history import SleeperBehaviorHistorySource


def test_sleeper_behavior_history_links_seasons_and_skips_cached_history() -> None:
    calls: list[str] = []

    def fake_get(url: str):
        calls.append(url)
        path = url.split("/v1", 1)[1]
        if path == "/league/current":
            return {"league_id": "current", "season": "2026", "previous_league_id": "oldest"}
        if path == "/league/oldest":
            return {"league_id": "oldest", "season": "2025", "previous_league_id": None}
        if path == "/league/current/rosters":
            return [{"roster_id": 1, "owner_id": "owner-a"}, {"roster_id": 2, "owner_id": "owner-b"}]
        if path == "/league/oldest/rosters":
            raise AssertionError("cached historical season should not be rescanned")
        if path == "/league/current/transactions/1":
            return [
                {
                    "transaction_id": "trade-1",
                    "status": "complete",
                    "type": "trade",
                    "created": 1785542400000,
                    "roster_ids": [1, 2],
                    "adds": {"p2": 1, "p1": 2},
                    "drops": {"p1": 1, "p2": 2},
                    "draft_picks": [
                        {
                            "season": "2027",
                            "round": 1,
                            "roster_id": 2,
                            "owner_id": 1,
                            "previous_owner_id": 2,
                        }
                    ],
                    "waiver_budget": [{"sender": 1, "receiver": 2, "amount": 7}],
                }
            ]
        if path.startswith("/league/current/transactions/"):
            return []
        raise AssertionError(path)

    source = SleeperBehaviorHistorySource(http_get_json=fake_get, max_workers=2)
    history = source.fetch_history(
        "current",
        skip_league_ids=frozenset({"oldest"}),
        player_positions={"p1": "QB", "p2": "RB"},
    )

    assert history.league_family_id == "sleeper-family:oldest"
    assert history.league_chain == ("oldest", "current")
    assert len(history.events) == 2
    owner_a = next(event for event in history.events if event.owner_id == "owner-a")
    owner_b = next(event for event in history.events if event.owner_id == "owner-b")
    assert owner_a.kind == BehavioralEventKind.TRADE
    assert {asset.kind for asset in owner_a.acquired} == {BehavioralAssetKind.PLAYER, BehavioralAssetKind.PICK}
    assert {asset.kind for asset in owner_a.disposed} == {BehavioralAssetKind.PLAYER, BehavioralAssetKind.FAAB}
    assert owner_a.counterparty_owner_ids == ("owner-b",)
    assert owner_b.counterparty_owner_ids == ("owner-a",)
    assert not any("/league/oldest/transactions/" in call for call in calls)
