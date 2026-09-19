from fsffl.value.calibration import DataRightsClass
from fsffl.value.sources.statsguy import normalize_statsguy_rankings


def test_normalizes_statsguy_rankings_with_snapshot_time():
    payload = '''
    {
      "format": "sf_dynasty",
      "asOf": "2026-08-04T13:01:35.221Z",
      "rankings": [
        {"rank": 3, "id": "7564", "name": "Ja'Marr Chase", "position": "WR", "value": 9466}
      ]
    }
    '''
    result = normalize_statsguy_rankings(
        payload,
        asset_id_by_sleeper_id={"7564": "research:sleeper:7564"},
        format_context_id="dynasty:sf",
        provenance_uri="https://api.statsguyfantasy.com/api/v1/rankings?format=sf_dynasty",
    )
    assert result.rows_seen == 1
    assert result.rows_imported == 1
    assert result.rows_unmapped == 0
    row = result.observations[0]
    assert row.asset_id == "research:sleeper:7564"
    assert row.value == 9466
    assert row.observed_at.isoformat() == "2026-08-04T13:01:35.221000+00:00"
    assert row.rights_class == DataRightsClass.RUNTIME_ONLY


def test_statsguy_date_only_history_is_available_at_end_of_utc_day():
    payload = '''
    {
      "asOf": "2025-09-08",
      "rankings": [{"id": "7564", "value": 9000}]
    }
    '''
    result = normalize_statsguy_rankings(
        payload,
        asset_id_by_sleeper_id={"7564": "research:sleeper:7564"},
        format_context_id="dynasty:sf",
    )
    assert result.observations[0].observed_at.isoformat() == "2025-09-08T23:59:59.999999+00:00"


def test_statsguy_counts_unmapped_rows():
    payload = '''
    {
      "asOf": "2026-08-04T13:01:35Z",
      "rankings": [{"id": "unknown", "value": 1000}]
    }
    '''
    result = normalize_statsguy_rankings(
        payload,
        asset_id_by_sleeper_id={},
        format_context_id="dynasty:sf",
    )
    assert result.rows_unmapped == 1
    assert result.observations == ()
