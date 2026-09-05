from pathlib import Path


def test_current_roster_role_uses_canonical_sleeper_state() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")

    assert "function playerDisplayRole(player){return player.roster_slot}" in source
    assert "role=playerDisplayRole(player)" in source
    assert "player.projected_starter?'Projected starter':'—'" in source
