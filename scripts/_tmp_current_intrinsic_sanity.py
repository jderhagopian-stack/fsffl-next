from __future__ import annotations

from datetime import UTC, datetime

from fsffl.forecast.career import build_multi_year_forecast
from fsffl.forecast.intrinsic_v1 import materialize_intrinsic_v1_forecast_path
from fsffl.forecast.models import ForecastDistribution
from fsffl.forecast.non_qb_career_state import _transition
from fsffl.forecast.qb_career_state_runtime import forecast_qb_career_state_runtime
from fsffl.state.models import Player, PlayerState, PlayerStatus, Position, Provenance, ProviderRef
from fsffl.value.intrinsic_v2 import estimate_intrinsic_value_v2

AS_OF = datetime(2026, 9, 12, 1, 5, 19, tzinfo=UTC)
PROVENANCE = Provenance(source="persisted-current-forecast-sanity", retrieved_at=AS_OF, effective_at=AS_OF)

# Point-in-time validation fixture from durable current Forecast artifact id 163 and
# matching canonical state c109dae9... . Stable NFL draft-pick facts are included
# solely to exercise the governed residual-pedigree path. This file is temporary
# validation evidence and is removed before production handoff.
ROWS = [
    # name, sleeper id, pos, age, Y1 mean, Y1 sd, draft pick, QB production percentile
    ("Josh Allen", "4984", "QB", 30, 388.0555, 208.8451987163231, 7, 1.0),
    ("Lamar Jackson", "4881", "QB", 29, 329.128, 177.13137054649653, 32, 0.933333333333333),
    ("Drake Maye", "11564", "QB", 24, 334.793, 180.18018199415795, 3, 0.983333333333333),
    ("Dak Prescott", "3294", "QB", 33, 312.358, 168.1060275672764, 135, 0.9),
    ("Sam Darnold", "4943", "QB", 29, 287.6005, 154.78194117442965, 3, 0.683333333333333),
    ("Drew Lock", "5854", "QB", 29, 2.7755, 1.4937292450104553, 42, 0.0),
    ("Bijan Robinson", "9509", "RB", 24, 331.248, 188.09693698845163, 8, None),
    ("Quinshon Judkins", "12512", "RB", 22, 210.4705, 119.51425027902931, 36, None),
    ("Rhamondre Stevenson", "7611", "RB", 28, 165.103, 93.75262216709031, 120, None),
    ("Tyler Allgeier", "8132", "RB", 26, 89.6405, 50.90175179959818, 151, None),
    ("Jonathon Brooks", "11583", "RB", 23, 165.548, 94.00531240811775, 46, None),
    ("Derrick Henry", "3198", "RB", 32, 259.1655, 147.1653767662916, 45, None),
    ("Trevor Etienne", "12531", "RB", 22, 7.5605, 4.293178802894473, None, None),
    ("CeeDee Lamb", "6786", "WR", 27, 214.4855, 110.92139549549066, 17, None),
    ("Tee Higgins", "6801", "WR", 27, 183.628, 94.9634078389726, 33, None),
    ("Zay Flowers", "9997", "WR", 26, 197.848, 102.317295369579, 22, None),
    ("DeVonta Smith", "7525", "WR", 27, 185.5505, 95.95763067846562, 10, None),
    ("KC Concepcion", "13298", "WR", 21, 123.068, 63.64474195616507, 24, None),
    ("Jaxon Smith-Njigba", "9488", "WR", 24, 246.3755, 127.41334158206152, 20, None),
    ("Troy Franklin", "11627", "WR", 23, 42.433, 21.94426930986083, 102, None),
    ("Devin Duvernay", "6847", "WR", 29, 1.4605, 1.02435345462394, 92, None),
    ("Brock Bowers", "11604", "TE", 23, 189.228, 106.98253129903512, 13, None),
    ("Kyle Pitts", "7553", "TE", 25, 146.353, 82.74258779465877, 4, None),
    ("Dallas Goedert", "5022", "TE", 31, 125.6005, 71.0098897754268, 49, None),
    ("Elijah Arroyo", "12521", "TE", 23, 55.1805, 31.197019301300063, 50, None),
    ("Ja'Tavion Sanders", "11600", "TE", 23, 13.1855, 7.454595337071828, 101, None),
]


def build(name, sid, pos_text, age, mean, sd, pick, qb_pct):
    pos = Position(pos_text)
    player_id = f"sleeper:player:{sid}"
    player = Player(
        player_id=player_id,
        full_name=name,
        position=pos,
        provider_refs=(ProviderRef(provider="sleeper", external_id=sid),),
    )
    state = PlayerState(
        player_id=player_id,
        as_of=AS_OF,
        age_years=float(age),
        draft_number=pick,
        status=PlayerStatus.ACTIVE,
        provenance=PROVENANCE,
    )
    base = ForecastDistribution(mean=mean, stddev=sd)
    bounded = None
    qb = None
    if pos in {Position.RB, Position.WR, Position.TE}:
        bounded = build_multi_year_forecast(base, (_transition(pos, age), _transition(pos, age + 1)))
    elif qb_pct is not None:
        qb = forecast_qb_career_state_runtime(
            player=player,
            player_state=state,
            evaluation_season=2026,
            production_percentile=qb_pct,
        )
    path = materialize_intrinsic_v1_forecast_path(
        player_id=player_id,
        position=pos,
        evaluation_as_of=AS_OF,
        base_distribution=base,
        base_forecast_model_version="next8-live-forecast-evidence-v3/current-artifact-163",
        bounded_path=bounded,
        qb_career_state=qb,
    )
    estimate = estimate_intrinsic_value_v2(player_path=path, player_state=state)
    return path, estimate


print("| Player | Pos | Y1 | Y2 | Y3 | post-Y3 | residual | raw Intrinsic | display | evidence |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
for row in ROWS:
    path, estimate = build(*row)
    means = [point.distribution.mean for point in path.horizons]
    print(
        f"| {row[0]} | {row[2]} | {means[0]:.1f} | {means[1]:.1f} | {means[2]:.1f} | "
        f"{estimate.raw_terminal_value:.1f} | {estimate.residual_fundamental_value:+.1f} | "
        f"{estimate.fundamental_value:.1f} | {estimate.display_value} | {estimate.evidence_state.value} |"
    )
