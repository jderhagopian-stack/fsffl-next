from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "src" / "fsffl" / "product"


def test_persistent_webapp_installs_distinct_league_value_lens_route() -> None:
    webapp = (PRODUCT / "persistent_webapp.py").read_text(encoding="utf-8")
    routes = (PRODUCT / "league_value_lens_routes.py").read_text(encoding="utf-8")
    assert "install_league_value_lens_routes" in webapp
    assert '"/api/league/value-lenses"' in routes
    assert "build_league_value_lenses" in routes
    assert "Broad Market remains independently usable" in routes


def test_atlas_lens_contract_cannot_create_team_value_or_team_utility() -> None:
    source = (PRODUCT / "league_value_lenses.py").read_text(encoding="utf-8")
    assert '"team_value_total_created": False' in source
    assert '"team_value_rank_created": False' in source
    assert '"league_market_value_available": False' in source
    assert '"team_utility_included": False' in source
    assert '"fsffl_cardinal_value_included": False' in source
    assert '"raw_value_subtraction_used": False' in source
    assert '"recommendation_authority": False' in source
    assert '"acceptance_probability": None' in source


def test_primary_league_presentation_uses_approved_value_hierarchy() -> None:
    html = (PRODUCT / "static" / "index.html").read_text(encoding="utf-8")
    corrections = (PRODUCT / "static" / "beta_product_corrections.js").read_text(encoding="utf-8")
    league = (PRODUCT / "static" / "league_comparison.js").read_text(encoding="utf-8")
    assert 'value="total_cardinal_value"' not in html
    assert 'option[value="total_cardinal_value"]' in corrections
    assert "remove()" in corrections
    assert "Broad Market + FSFFL Intrinsic" in league
    assert "Total FSFFL Cardinal Value" not in league


def test_player_board_intrinsic_build_is_optional_not_route_blocking() -> None:
    routes = (PRODUCT / "league_value_lens_routes.py").read_text(encoding="utf-8")
    assert '"status": "building_optional"' in routes
    assert '"Broad Market remains independently usable."' in routes
    assert "JSONResponse(status_code=202" not in routes
    assert 'payload["fsffl_intrinsic"]' in routes


def test_market_value_lens_route_exposes_intrinsic_coordinate_and_build_state() -> None:
    routes = (PRODUCT / "league_value_lens_routes.py").read_text(encoding="utf-8")
    for token in (
        '"intrinsic_execution"',
        '"forecast_coordinate"',
        '"response_budget_exceeded"',
        '"started_at"',
        '"updated_at"',
        "FSFFL Market value lenses",
    ):
        assert token in routes
    assert '"all_player_forecast"' not in routes or "forecast_status" in routes


def test_hosted_readiness_does_not_restore_intrinsic_from_foreground_reads() -> None:
    webapp = (PRODUCT / "persistent_webapp.py").read_text(encoding="utf-8")
    readiness = webapp.split("def _hosted_capability_readiness", 1)[1].split(
        "def _reconcile_hosted_intrinsic", 1
    )[0]
    reconcile = webapp.split("def _reconcile_hosted_intrinsic", 1)[1].split(
        "# Reuse only exact Decision-owned package economics", 1
    )[0]

    assert "_shapley_intrinsic_coordinator.current(context)" in readiness
    assert "restore_compatible(" not in readiness
    assert "restore_compatible_staged" in reconcile
    assert "wait_for_terminal(context)" in reconcile


def test_first_load_stages_only_until_core_forecast_or_team_is_missing() -> None:
    routes = (PRODUCT / "league_value_lens_routes.py").read_text(encoding="utf-8")
    branch = routes.split("if background_coordinator is not None:", 1)[1]
    staging_index = branch.index("first_load_staging = bool(")
    staged_return_index = branch.index("return payload")
    current_index = branch.index("background_coordinator.current(runtime)")

    assert staging_index < staged_return_index < current_index
    assert 'runtime.publication_generation_id is None' in branch
    assert 'runtime.forecast_evidence is None' in branch
    assert 'runtime_store.working_generation_active(user_id)' not in branch
    assert '"status": "loading"' in branch[:staged_return_index]
    assert '"status": "staged"' in branch[:staged_return_index]
    assert '"players": []' in branch[:staged_return_index]


def test_staged_intrinsic_restore_failure_falls_back_to_background_lifecycle() -> None:
    webapp = (PRODUCT / "persistent_webapp.py").read_text(encoding="utf-8")
    reconcile = webapp.split("def _reconcile_hosted_intrinsic", 1)[1].split(
        "# Reuse only exact Decision-owned package economics", 1
    )[0]

    staged_index = reconcile.index("restore_compatible_staged")
    warning_index = reconcile.index("FSFFL staged Intrinsic restore unavailable")
    fallback_index = reconcile.index("wait_for_terminal(context)")
    assert staged_index < warning_index < fallback_index
    assert "except IntrinsicBuildSuperseded:" in reconcile
    assert "except Exception as exc:" in reconcile
