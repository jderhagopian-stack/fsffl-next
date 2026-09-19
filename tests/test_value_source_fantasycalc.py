from datetime import UTC, datetime

from fsffl.value.calibration import DataRightsClass
from fsffl.value.sources.fantasycalc import normalize_fantasycalc_values


def test_normalizes_fantasycalc_current_values_with_explicit_timestamp_and_identity():
    payload = '''
    [
      {
        "player": {"name": "Josh Allen", "sleeperId": "4984"},
        "value": 10123,
        "overallRank": 1,
        "positionRank": 1
      }
    ]
    '''
    observed_at = datetime(2026, 9, 5, 12, 45, tzinfo=UTC)

    result = normalize_fantasycalc_values(
        payload,
        observed_at=observed_at,
        asset_id_by_sleeper_id={"4984": "player:josh-allen"},
        format_context_id="dynasty:sf:12:half",
        source_version="fixture",
        provenance_uri="https://api.fantasycalc.com/values/current",
    )

    assert result.rows_seen == 1
    assert result.rows_imported == 1
    assert result.rows_unmapped == 0
    observation = result.observations[0]
    assert observation.source_id == "fantasycalc_market_values"
    assert observation.asset_id == "player:josh-allen"
    assert observation.value == 10123
    assert observation.observed_at == observed_at
    assert observation.rights_class == DataRightsClass.RUNTIME_ONLY


def test_fantasycalc_counts_unmapped_rows_without_guessing_identity():
    payload = '[{"player": {"sleeperId": "unknown"}, "value": 5000}]'
    result = normalize_fantasycalc_values(
        payload,
        observed_at=datetime(2026, 9, 5, 12, 45, tzinfo=UTC),
        asset_id_by_sleeper_id={},
        format_context_id="dynasty:sf:12:half",
    )

    assert result.rows_seen == 1
    assert result.rows_imported == 0
    assert result.rows_unmapped == 1
    assert result.observations == ()
