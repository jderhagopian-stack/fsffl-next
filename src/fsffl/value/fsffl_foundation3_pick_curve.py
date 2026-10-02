from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from .calibration import DataRightsClass
from .historical_pick import GovernedDraftSlotValue, GovernedDraftSlotValueCurve
from .models import ValueDistribution, ValueScale

FSFFL_FOUNDATION3_TARGET_LEAGUE_EXTERNAL_ID = "1312071960615731200"
FSFFL_FOUNDATION3_TARGET_LEAGUE_ID = (
    f"sleeper:{FSFFL_FOUNDATION3_TARGET_LEAGUE_EXTERNAL_ID}"
)
FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON = 2027
FSFFL_FOUNDATION3_CURVE_MODEL_VERSION = "fsffl-foundation3-exact-slot-economics-v1:2024-2026"
FSFFL_FOUNDATION3_RAW_SOURCE_RIGHTS_CLASS = DataRightsClass.RESEARCH_ONLY
FSFFL_FOUNDATION3_DEPLOYMENT_SCOPE = "private_beta_frozen_derived_parameters"
FSFFL_FOUNDATION3_COMMERCIAL_RECHECK_REQUIRED = True
FSFFL_FOUNDATION3_RIGHTS_BASIS = (
    "Private-beta deployment is limited to the frozen 36-slot derived parameter "
    "curve. Raw DynastyProcess/FantasyPros-lineage rows remain RESEARCH_ONLY and "
    "are not deployed or redistributed. Commercial use requires a fresh rights review."
)
FSFFL_FOUNDATION3_SCALE = ValueScale(
    scale_id="dynastyprocess-2qb-pit",
    version="foundation3-v1",
    unit_label="DynastyProcess 2QB value units",
)
FSFFL_FOUNDATION3_EVIDENCE_AS_OF = datetime(
    2026, 7, 11, 16, 13, 0, 974000, tzinfo=UTC
)
FSFFL_FOUNDATION3_EVIDENCE_SEASONS = (2024, 2025, 2026)
FSFFL_FOUNDATION3_SOURCE_MODEL_VERSIONS = (
    "foundation3-fsffl-historical-draft-freeze-v1+a106fdf7188cf0e9e48531fd396d5fd64c96204b",
    "foundation3-fsffl-historical-draft-freeze-v1+e5035554b465a6ee06d6344e12314fd7fdc805c4",
    "foundation3-fsffl-historical-draft-freeze-v1+41c11510c09b8dd8051844ffc9979b710e145150",
)
FSFFL_FOUNDATION3_PROVENANCE = (
    "DynastyProcess 2QB point-in-time player value frozen before each completed FSFFL rookie draft; weekly public git history; selection=Sleeper completed rookie draft 1049056120377090049; values frozen at draft start 2024-06-01T22:12:50.328000+00:00; market=github:dynastyprocess/data@a106fdf7188cf0e9e48531fd396d5fd64c96204b:files/values.csv",
    "DynastyProcess 2QB point-in-time player value frozen before each completed FSFFL rookie draft; weekly public git history; selection=Sleeper completed rookie draft 1195205225995415553; values frozen at draft start 2025-05-31T21:16:36.387000+00:00; market=github:dynastyprocess/data@e5035554b465a6ee06d6344e12314fd7fdc805c4:files/values.csv",
    "DynastyProcess 2QB point-in-time player value frozen before each completed FSFFL rookie draft; weekly public git history; selection=Sleeper completed rookie draft 1312071960619941888; values frozen at draft start 2026-07-11T16:13:00.974000+00:00; market=github:dynastyprocess/data@41c11510c09b8dd8051844ffc9979b710e145150:files/values.csv",
    "2023 FSFFL rookie draft excluded by the explicit 14-day freshness gate: latest retained DynastyProcess snapshot was 18 days before draft start.",
    FSFFL_FOUNDATION3_RIGHTS_BASIS,
)


def _slot(
    slot: int,
    mean: float,
    stddev: float,
    adjusted: bool,
) -> GovernedDraftSlotValue:
    return GovernedDraftSlotValue(
        slot_in_round=slot,
        value=ValueDistribution(mean=mean, stddev=stddev),
        evidence_seasons=FSFFL_FOUNDATION3_EVIDENCE_SEASONS,
        source_model_versions=FSFFL_FOUNDATION3_SOURCE_MODEL_VERSIONS,
        provenance=FSFFL_FOUNDATION3_PROVENANCE,
        dominance_adjusted=adjusted,
    )


def _curve_economics_payload(
    curves: tuple[GovernedDraftSlotValueCurve, ...],
) -> list[dict[str, object]]:
    """Canonicalize only the frozen economic parameters and their evidence lineage."""

    return [
        {
            "round": curve.round,
            "scale": curve.scale.model_dump(mode="json"),
            "slots": [
                {
                    "slot_in_round": row.slot_in_round,
                    "value": row.value.model_dump(mode="json"),
                    "evidence_seasons": sorted(row.evidence_seasons),
                    "source_model_versions": sorted(row.source_model_versions),
                    "dominance_adjusted": row.dominance_adjusted,
                }
                for row in curve.slots
            ],
        }
        for curve in curves
    ]


def foundation3_curve_economics_sha256(
    curves: tuple[GovernedDraftSlotValueCurve, ...],
) -> str:
    payload = _curve_economics_payload(curves)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


FSFFL_FOUNDATION3_CURVES = (
    GovernedDraftSlotValueCurve(
        round=1,
        as_of=FSFFL_FOUNDATION3_EVIDENCE_AS_OF,
        scale=FSFFL_FOUNDATION3_SCALE,
        slots=(
            _slot(1, 6434.333333333333, 664.4427907820385, False),
            _slot(2, 4656.333333333333, 2074.636085892871, False),
            _slot(3, 4109.666666666667, 1159.9064138493623, False),
            _slot(4, 4078.0, 880.0060605851916, False),
            _slot(5, 2815.1666666666665, 268.58482003932556, True),
            _slot(6, 2815.1666666666665, 1219.9616683413558, True),
            _slot(7, 1851.6666666666667, 810.1170011520284, False),
            _slot(8, 1829.0, 988.0833298192349, False),
            _slot(9, 1646.6666666666667, 672.8755869813937, False),
            _slot(10, 1555.0, 365.71664805784616, False),
            _slot(11, 965.2222222222222, 390.4524599189894, True),
            _slot(12, 965.2222222222222, 405.4881526941431, True),
        ),
        model_version=FSFFL_FOUNDATION3_CURVE_MODEL_VERSION,
    ),
    GovernedDraftSlotValueCurve(
        round=2,
        as_of=FSFFL_FOUNDATION3_EVIDENCE_AS_OF,
        scale=FSFFL_FOUNDATION3_SCALE,
        slots=(
            _slot(1, 965.2222222222222, 396.29797680502105, True),
            _slot(2, 909.3333333333334, 472.6466850501428, False),
            _slot(3, 669.1666666666666, 376.2656050658305, True),
            _slot(4, 669.1666666666666, 583.769194307324, True),
            _slot(5, 640.6666666666666, 445.82831772879666, False),
            _slot(6, 473.8333333333333, 205.92831816489505, True),
            _slot(7, 473.8333333333333, 94.95861671743594, True),
            _slot(8, 370.5, 156.96151332943583, True),
            _slot(9, 370.5, 251.32631510979238, True),
            _slot(10, 340.0, 27.940412786261255, False),
            _slot(11, 258.22222222222223, 123.318667796731, True),
            _slot(12, 258.22222222222223, 123.72255899769561, True),
        ),
        model_version=FSFFL_FOUNDATION3_CURVE_MODEL_VERSION,
    ),
    GovernedDraftSlotValueCurve(
        round=3,
        as_of=FSFFL_FOUNDATION3_EVIDENCE_AS_OF,
        scale=FSFFL_FOUNDATION3_SCALE,
        slots=(
            _slot(1, 258.22222222222223, 156.74741811723644, True),
            _slot(2, 194.75, 66.3907310297655, True),
            _slot(3, 194.75, 103.74839356186037, True),
            _slot(4, 194.75, 116.26576953973455, True),
            _slot(5, 194.75, 66.94945232536756, True),
            _slot(6, 193.33333333333334, 72.58864312763474, True),
            _slot(7, 193.33333333333334, 71.63410112819484, True),
            _slot(8, 193.33333333333334, 398.68046241458967, True),
            _slot(9, 124.44444444444444, 56.962734190168156, True),
            _slot(10, 124.44444444444444, 110.94515383960594, True),
            _slot(11, 124.44444444444444, 76.96640280339099, True),
            _slot(12, 120.0, 54.7905101272109, False),
        ),
        model_version=FSFFL_FOUNDATION3_CURVE_MODEL_VERSION,
    ),
)

FSFFL_FOUNDATION3_EVIDENCE_SHA256 = foundation3_curve_economics_sha256(
    FSFFL_FOUNDATION3_CURVES
)


def fsffl_foundation3_live_curves(
    *,
    league_id: str,
    draft_season: int,
    team_count: int,
    rookie_draft_rounds: int,
) -> tuple[GovernedDraftSlotValueCurve, ...]:
    """Return frozen economics only for the governed 2027 FSFFL coordinate."""

    if (
        league_id != FSFFL_FOUNDATION3_TARGET_LEAGUE_ID
        or draft_season != FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON
        or team_count != 12
        or rookie_draft_rounds != 3
    ):
        return ()
    return FSFFL_FOUNDATION3_CURVES
