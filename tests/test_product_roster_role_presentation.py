from pathlib import Path


def test_current_roster_role_uses_canonical_sleeper_state() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")

    assert "function playerDisplayRole(player){return player.roster_slot}" in source
    assert "role=playerDisplayRole(player)" in source
    assert "player.projected_starter?'Projected starter':'—'" in source


def test_current_roster_orders_actual_starters_before_bench_and_reserve() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")

    assert "currentRosterRoleOrder={QB:0,RB:1,WR:2,TE:3,FLEX:4,SUPERFLEX:5,K:6,DST:7,BENCH:8,TAXI:9,IR:10}" in source
    assert "function currentRosterPlayers(players)" in source
    assert "currentRosterPlayers(view.players).forEach" in source
