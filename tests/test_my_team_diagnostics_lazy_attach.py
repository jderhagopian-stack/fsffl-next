from pathlib import Path


def test_my_team_diagnostics_attach_after_lazy_dashboard_load() -> None:
    diagnostics = Path("src/fsffl/product/static/my_team_diagnostics.js").read_text()
    product_shell = Path("src/fsffl/product/static/product_shell.js").read_text()
    index = Path("src/fsffl/product/static/index.html").read_text()

    assert "my_team_diagnostics.js" in index
    assert "my_team_dashboard.js" not in index
    assert "ensureMyTeamScript" in product_shell
    assert "lazyProductScript('renderFsfflMyTeam','/static/my_team_dashboard.js'" in product_shell

    # The diagnosis helper loads with the initial shell while My Team remains lazy.
    # It must therefore attach when the lazy dashboard publishes its renderer rather
    # than giving up permanently because renderMyTeamCommandCenter is initially absent.
    assert "Object.defineProperty(window,'renderFsfflMyTeam'" in diagnostics
    assert "set(value)" in diagnostics
    assert "attachDiagnostics()" in diagnostics
    assert "renderFsfflMyTeamDiagnostics()" in diagnostics
    assert "What is actually shaping this team?" in diagnostics
    assert "Position to investigate" in diagnostics
    assert "One-player exposure" in diagnostics
    assert "Owned-pick trajectory" in diagnostics


def test_my_team_diagnostics_remain_presentation_only() -> None:
    diagnostics = Path("src/fsffl/product/static/my_team_diagnostics.js").read_text()

    assert "api(" not in diagnostics
    assert "fetch(" not in diagnostics
    assert "franchise-health score" in diagnostics
    assert "No youth/veteran label or age-curve value adjustment is created in Presentation." in diagnostics
    assert "no new pick-value score is calculated here" in diagnostics
