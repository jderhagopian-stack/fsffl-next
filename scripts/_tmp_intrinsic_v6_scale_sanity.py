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
STRUCTURAL = {
    Position.QB: (1.8185139181912202, 24, 37.406054001042406),
    Position.RB: (1.1693918805062957, 35, 84.83113044982792),
    Position.WR: (0.8877723628387252, 37, 118.12651384978479),
    Position.TE: (0.517353465645913, 12, 65.74173591413089),
}
RAW_QUANTILES = (
    (2180.0118331871763, ">p99.9"),
    (1757.2847049325596, "p99.5-p99.9"),
    (1540.989083049095, "p99-p99.5"),
    (1104.6001017928277, "p97-p99"),
    (793.3000646748549, "p95-p97"),
    (428.501161719536, "p90-p95"),
    (222.27465691463885, "p75-p90"),
    (95.2335316536557, "p50-p75"),
    (25.147489994747453, "p20-p50"),
    (6.344082606271767, "p05-p20"),
    (0.0, "<p05"),
)
ROWS = [
    ("Josh Allen", "4984", "QB", 30, 388.0555, 208.8451987163231, 7, 1.0),
    ("Lamar Jackson", "4881", "QB", 29, 329.128, 177.13137054649653, 32, .933333333333333),
    ("Drake Maye", "11564", "QB", 24, 334.793, 180.18018199415795, 3, .983333333333333),
    ("Dak Prescott", "3294", "QB", 33, 312.358, 168.1060275672764, 135, .9),
    ("Sam Darnold", "4943", "QB", 29, 287.6005, 154.78194117442965, 3, .683333333333333),
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


def ref_band(raw: float) -> str:
    for cutoff, label in RAW_QUANTILES:
        if raw >= cutoff:
            return label
    return "<p05"


def build(row):
    name, sleeper_id, pos_text, age, mean, sd, pick, qb_pct = row
    pos = Position(pos_text)
    player_id = f"sleeper:player:{sleeper_id}"
    player = Player(player_id=player_id, full_name=name, position=pos, provider_refs=(ProviderRef(provider="sleeper", external_id=sleeper_id),))
    state = PlayerState(player_id=player_id, as_of=AS_OF, age_years=float(age), draft_number=pick, status=PlayerStatus.ACTIVE, provenance=PROVENANCE)
    base = ForecastDistribution(mean=mean, stddev=sd)
    bounded = None
    qb = None
    if pos in {Position.RB, Position.WR, Position.TE}:
        bounded = build_multi_year_forecast(base, (_transition(pos, age), _transition(pos, age + 1)))
    elif qb_pct is not None:
        qb = forecast_qb_career_state_runtime(player=player, player_state=state, evaluation_season=2026, production_percentile=qb_pct)
    path = materialize_intrinsic_v1_forecast_path(
        player_id=player_id,
        position=pos,
        evaluation_as_of=AS_OF,
        base_distribution=base,
        base_forecast_model_version="next8-live-forecast-evidence-v3/current-artifact-163",
        bounded_path=bounded,
        qb_career_state=qb,
    )
    factor, starters, supply = STRUCTURAL[pos]
    estimate = estimate_intrinsic_value_v2(
        player_path=path,
        player_state=state,
        structural_factor=factor,
        structural_starter_demand=starters,
        structural_effective_supply=supply,
    )
    return path, estimate


print("| Player | Pos | Age | Forecast Y1→Y2→Y3 | Pre-structural | Structural factor | Economic raw | PIT ref band | Intrinsic | Broad Market |")
print("|---|---:|---:|---|---:|---:|---:|---|---:|---|")
for row in ROWS:
    path, estimate = build(row)
    means = [point.distribution.mean for point in path.horizons]
    trajectory = f"{means[0]:.0f}→{means[1]:.0f}→{means[2]:.0f}"
    print(
        f"| {row[0]} | {row[2]} | {row[3]} | {trajectory} | {estimate.pre_structural_fundamental_value:.1f} | "
        f"{estimate.structural_factor:.3f} | {estimate.fundamental_value:.1f} | {ref_band(estimate.fundamental_value)} | "
        f"{estimate.display_value} | n/a in sanity fixture |"
    )
