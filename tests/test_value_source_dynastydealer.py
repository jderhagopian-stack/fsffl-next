from fsffl.value.calibration import DataRightsClass
from fsffl.value.sources.dynastydealer import normalize_dynastydealer_values


def test_normalizes_dynastydealer_player_values_with_explicit_identity_crosswalk():
    payload = '''
    {
      "source": "tidb",
      "players": [
        {
          "sleeper_id": "4984",
          "name": "Josh Allen",
          "position": "QB",
          "team": "BUF",
          "base_value": 10000,
          "current_value": 9927,
          "votes": 302,
          "updated_at": "2026-06-11T21:03:26.000Z",
          "age": 30
        }
      ],
      "total": 1
    }
    '''

    result = normalize_dynastydealer_values(
        payload,
        asset_id_by_sleeper_id={"4984": "player:josh-allen"},
        format_context_id="dynasty:sf:12:half",
        source_version="fixture",
        provenance_uri="https://www.dynastydealer.com/api/player-values",
    )

    assert result.rows_seen == 1
    assert result.rows_imported == 1
    assert result.rows_unmapped == 0
    observation = result.observations[0]
    assert observation.asset_id == "player:josh-allen"
    assert observation.value == 9927
    assert observation.format_context_id == "dynasty:sf:12:half"
    assert observation.rights_class == DataRightsClass.RUNTIME_ONLY
    assert observation.observed_at.isoformat() == "2026-06-11T21:03:26+00:00"


def test_dynastydealer_counts_unmapped_rows_instead_of_guessing_identity():
    payload = '''
    {
      "players": [
        {
          "sleeper_id": "unknown",
          "current_value": 5000,
          "updated_at": "2026-06-11T21:03:26Z"
        }
      ]
    }
    '''

    result = normalize_dynastydealer_values(
        payload,
        asset_id_by_sleeper_id={},
        format_context_id="dynasty:sf:12:half",
    )

    assert result.rows_seen == 1
    assert result.rows_imported == 0
    assert result.rows_unmapped == 1
    assert result.observations == ()
