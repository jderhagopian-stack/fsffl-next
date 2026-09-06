from pathlib import Path


def test_home_leads_with_user_tasks_not_pipeline_internals() -> None:
    source = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
    for label in (
        "Review My Team",
        "Compare the League",
        "Browse Players & Assets",
        "Analyze a Trade",
        "Explore Analytics",
        "Open Reports",
    ):
        assert label in source
    assert "Start with the question you want answered." in source
    assert "Show technical status" in source
    assert "grid.hidden=true" in source


def test_home_is_navigation_only_and_mobile_responsive() -> None:
    source = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "ensureHomeScript" in shell
    assert "installFsfflHomeExperience" in shell
    assert "api(" not in source
    assert "expected_wins" not in source
    assert "acceptance_probability" not in source
    assert "@media(max-width:760px)" in source
    assert "@media(max-width:460px)" in source
