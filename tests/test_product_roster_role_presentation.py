from pathlib import Path


def test_roster_role_uses_projected_lineup_not_stale_sleeper_starter_slot() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")

    assert "function playerDisplayRole(player)" in source
    assert "player.projected_starter&&player.projected_lineup_slot" in source
    assert "['TAXI','IR'].includes(player.roster_slot)" in source
    assert "return 'BENCH'" in source
    assert "role=playerDisplayRole(player)" in source
