from fsffl.value import DataRightsClass
from fsffl.value.sources import normalize_dynastyprocess_values


CSV = '''"player","pos","team","age","draft_year","ecr_1qb","ecr_2qb","ecr_pos","value_1qb","value_2qb","scrape_date","fp_id"
"Player One","WR","AAA",25.0,2022,1,2,1,9000,8000,"2026-09-04","100"
"Player Two","RB","BBB",24.0,2023,3,4,1,7000,6500,"2026-09-04","200"
'''


def test_dynastyprocess_normalization_uses_canonical_crosswalk_and_two_contexts() -> None:
    result = normalize_dynastyprocess_values(
        CSV,
        asset_id_by_fp_id={"100": "player:one"},
        source_version="snapshot-v1",
        provenance_uri="https://example.test/source",
    )

    assert result.rows_seen == 2
    assert result.rows_imported == 1
    assert result.rows_unmapped == 1
    assert len(result.observations) == 2
    assert {row.asset_id for row in result.observations} == {"player:one"}
    assert {row.format_context_id for row in result.observations} == {
        "dynasty:1qb",
        "dynasty:2qb",
    }
    assert {row.value for row in result.observations} == {9000.0, 8000.0}
    assert all(row.rights_class == DataRightsClass.RESEARCH_ONLY for row in result.observations)


def test_dynastyprocess_normalization_fails_closed_on_schema_drift() -> None:
    bad_csv = '"player","scrape_date","fp_id"\n"Player One","2026-09-04","100"\n'

    try:
        normalize_dynastyprocess_values(bad_csv, asset_id_by_fp_id={"100": "player:one"})
    except ValueError as exc:
        assert "missing required columns" in str(exc)
    else:
        raise AssertionError("expected schema validation failure")


def test_dynastyprocess_rights_class_must_be_explicitly_promoted() -> None:
    result = normalize_dynastyprocess_values(
        CSV,
        asset_id_by_fp_id={"100": "player:one", "200": "player:two"},
        rights_class=DataRightsClass.PUBLIC_REDISTRIBUTABLE,
    )
    assert all(
        row.rights_class == DataRightsClass.PUBLIC_REDISTRIBUTABLE
        for row in result.observations
    )
