from __future__ import annotations

import base64
import json
import math
import zlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping

from fsffl.state.models import Player, PlayerState

QB_CAREER_STATE_MODEL_VERSION = "qb-career-state-logit-v1"
QB_CAREER_STATE_EVIDENCE_VERSION = "qb-career-state-evidence-v1"
QB_CAREER_STATE_TRAINING_CUTOFF_SEASON = 2021
MEANINGFUL_STARTER_PASS_ATTEMPTS = 200

# Exact deployment-shaped model used by the final 2022 chronological holdout.
_FEATURE_NAMES = (
    "age",
    "experience",
    "draft_pick_pct",
    "games_pct",
    "opportunity_pct",
    "role_mean_2",
    "role_vol_2",
    "qb_established_starter_seasons",
    "production_percentile",
    "horizon",
)
_MEANS = (
    28.17161410018553, 5.4475881261595545, 0.6141198845280509,
    0.453266533886282, 0.4372495532859275, 0.4384827941007782,
    0.10646861994832389, 2.580705009276438, 0.5, 1.481447124304267,
)
_SCALES = (
    4.466246467224788, 4.40162926585104, 0.3695569498147479,
    0.401266586152191, 0.3496247847323222, 0.33754003616785283,
    0.1449288068700335, 3.3910936858303966, 0.28864410744531577,
    0.49965567224181157,
)
_BETA = (
    -0.7474262942513274, -0.5449219783314777, -0.22610555473847563,
    0.056218927623285904, 0.26076559849785513, -0.4073951168157181,
    0.29282611386038354, 0.04571643278949464, 0.64876535448326,
    1.4668863850075404, -0.18756329093412563,
)

# 2026 season-scoped prior-football evidence. Built offline from nflverse 1999-2025
# regular-season stats + player/draft metadata. Compressed only to keep the runtime
# artifact compact; decoded content is versioned and validated before use.
_EVIDENCE_ZLIB_B64 = "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"


@dataclass(frozen=True)
class QBCareerStateEvidence:
    gsis_id: str
    evaluation_season: int
    feature_cutoff_season: int
    experience: float
    draft_pick_pct: float
    games_pct: float
    opportunity_pct: float
    role_mean_2: float
    role_vol_2: float
    established_starter_seasons: float


@dataclass(frozen=True)
class QBCareerStateForecast:
    model_version: str
    evidence_version: str
    evaluation_season: int
    feature_cutoff_season: int
    production_percentile: float
    year2_probability: float
    year3_probability: float


@lru_cache(maxsize=1)
def _evidence_payload() -> dict:
    payload = json.loads(zlib.decompress(base64.b64decode(_EVIDENCE_ZLIB_B64)))
    if payload.get("artifact_version") != QB_CAREER_STATE_EVIDENCE_VERSION:
        raise ValueError("QB career-state evidence artifact version mismatch")
    if payload.get("model_version") != QB_CAREER_STATE_MODEL_VERSION:
        raise ValueError("QB career-state model/evidence version mismatch")
    return payload


def _gsis_id(player: Player) -> str | None:
    for ref in player.provider_refs:
        if ref.provider.lower() == "gsis" and ref.external_id.strip():
            return ref.external_id.strip()
    return None


def resolve_qb_career_state_evidence(
    *,
    player: Player,
    player_state: PlayerState | None,
    evaluation_season: int,
) -> QBCareerStateEvidence | None:
    if player_state is None or player_state.age_years is None:
        return None
    payload = _evidence_payload()
    if payload.get("evaluation_season") != evaluation_season:
        return None
    gsis_id = _gsis_id(player)
    if gsis_id is None:
        return None
    row = payload.get("players", {}).get(gsis_id)
    if not isinstance(row, Mapping):
        return None
    cutoff = int(payload["feature_cutoff_season"])
    if int(row.get("feature_cutoff_season", -1)) != cutoff:
        return None
    return QBCareerStateEvidence(
        gsis_id=gsis_id,
        evaluation_season=evaluation_season,
        feature_cutoff_season=cutoff,
        experience=float(row["experience"]),
        draft_pick_pct=float(row["draft_pick_pct"]),
        games_pct=float(row["games_pct"]),
        opportunity_pct=float(row["opportunity_pct"]),
        role_mean_2=float(row["role_mean_2"]),
        role_vol_2=float(row["role_vol_2"]),
        established_starter_seasons=float(row["qb_established_starter_seasons"]),
    )


def rank_percentiles(values_by_player: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(values_by_player.items(), key=lambda item: (item[1], item[0]))
    n = len(ordered)
    if n == 0:
        return {}
    output: dict[str, float] = {}
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][1] == ordered[i][1]:
            j += 1
        rank = (i + j - 1) / 2.0
        pct = (rank + 0.5) / n
        for k in range(i, j):
            output[ordered[k][0]] = pct
        i = j
    return output


def _probability(*, age: float, evidence: QBCareerStateEvidence, production_percentile: float, horizon: int) -> float:
    raw = (
        age,
        evidence.experience,
        evidence.draft_pick_pct,
        evidence.games_pct,
        evidence.opportunity_pct,
        evidence.role_mean_2,
        evidence.role_vol_2,
        evidence.established_starter_seasons,
        production_percentile,
        float(horizon),
    )
    linear = _BETA[0]
    for idx, value in enumerate(raw):
        linear += _BETA[idx + 1] * ((value - _MEANS[idx]) / _SCALES[idx])
    linear = max(-35.0, min(35.0, linear))
    return 1.0 / (1.0 + math.exp(-linear))


def forecast_qb_career_state(
    *,
    player: Player,
    player_state: PlayerState | None,
    evaluation_season: int,
    production_percentile: float,
) -> QBCareerStateForecast | None:
    evidence = resolve_qb_career_state_evidence(
        player=player,
        player_state=player_state,
        evaluation_season=evaluation_season,
    )
    if evidence is None or player_state is None or player_state.age_years is None:
        return None
    p2 = _probability(
        age=float(player_state.age_years), evidence=evidence,
        production_percentile=production_percentile, horizon=1,
    )
    p3 = _probability(
        age=float(player_state.age_years), evidence=evidence,
        production_percentile=production_percentile, horizon=2,
    )
    return QBCareerStateForecast(
        model_version=QB_CAREER_STATE_MODEL_VERSION,
        evidence_version=QB_CAREER_STATE_EVIDENCE_VERSION,
        evaluation_season=evaluation_season,
        feature_cutoff_season=evidence.feature_cutoff_season,
        production_percentile=production_percentile,
        year2_probability=p2,
        year3_probability=p3,
    )


def model_feature_names() -> tuple[str, ...]:
    return _FEATURE_NAMES
