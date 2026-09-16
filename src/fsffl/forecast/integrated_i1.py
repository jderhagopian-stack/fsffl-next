from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

from fsffl.state.models import Position

from .football_state import CanonicalFootballStateEvidence
from .i1_config import FROZEN_I1_REGULARIZATION

I1_C = FROZEN_I1_REGULARIZATION.default_c
I1_RANDOM_SEED = 20260915
I1_MAX_ITER = 2000
I1_MIN_TRAINING_ROWS = 100
I1_MIN_BINARY_CLASS = 15
I1_MODEL_VERSION = f"integrated-i1-{FROZEN_I1_REGULARIZATION.version}"

STATE_NAMES = ("out", "depth", "usable", "starter", "premium", "elite")
POSITIVE_STATES = STATE_NAMES[1:]
USEFUL_STATES = frozenset(STATE_NAMES[2:])
STARTER_STATES = frozenset(STATE_NAMES[3:])
PREMIUM_STATES = frozenset(STATE_NAMES[4:])
POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


def age_band(position: Position | str, age_years: float | None) -> str:
    position_text = position.value if isinstance(position, Position) else str(position)
    if age_years is None:
        return "unknown"
    if position_text == "QB":
        return "young" if age_years <= 25 else ("prime" if age_years <= 31 else "aging")
    return "young" if age_years <= 23 else ("prime" if age_years <= 27 else "aging")


def experience_band(experience_years: int | None) -> str:
    if experience_years is None:
        return "unknown"
    if experience_years <= 1:
        return "0_1"
    if experience_years <= 3:
        return "2_3"
    if experience_years <= 6:
        return "4_6"
    return "7_plus"


def _quantile(values: Iterable[float], p: float) -> float:
    xs = sorted(float(value) for value in values)
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo = int(math.floor(z)); hi = int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    fraction = z - lo
    return xs[lo] * (1 - fraction) + xs[hi] * fraction


def fit_state_boundaries(values: Iterable[float], *, k: int = 5, iterations: int = 60) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Frozen research 1-D log-space k-means state boundary fit."""

    xs = sorted(math.log1p(max(0.0, float(value))) for value in values if value > 0)
    if len(xs) < k:
        center = sum(xs) / len(xs) if xs else 0.0
        centers = [center] * k
    else:
        centers = [_quantile(xs, (index + 0.5) / k) for index in range(k)]
    for _ in range(iterations):
        groups: list[list[float]] = [[] for _ in range(k)]
        for value in xs:
            index = min(range(k), key=lambda candidate: abs(value - centers[candidate]))
            groups[index].append(value)
        updated = [
            sum(group) / len(group) if group else centers[index]
            for index, group in enumerate(groups)
        ]
        updated.sort()
        if max(abs(a - b) for a, b in zip(updated, centers, strict=True)) < 1e-9:
            centers = updated
            break
        centers = updated
    raw = [max(0.0, math.expm1(value)) for value in centers]
    thresholds = [(raw[index] + raw[index + 1]) / 2 for index in range(k - 1)]
    return tuple(raw), tuple(thresholds)


def state_for_points(
    points: float,
    boundaries: tuple[tuple[float, ...], tuple[float, ...]],
) -> str:
    if points <= 0:
        return "out"
    _centers, thresholds = boundaries
    index = 0
    while index < len(thresholds) and points > thresholds[index]:
        index += 1
    return POSITIVE_STATES[index]


@dataclass(frozen=True)
class I1TrainingRow:
    position: Position
    age_band: str
    current_state: str
    horizon: int
    target_state: str
    target_points: float
    current_points: float
    prior_points: float | None
    experience_years: int | None
    evidence: CanonicalFootballStateEvidence | None = None

    def __post_init__(self) -> None:
        if self.position not in POSITIONS:
            raise ValueError("I1 supports QB/RB/WR/TE only")
        if self.current_state not in STATE_NAMES or self.target_state not in STATE_NAMES:
            raise ValueError("unknown I1 career state")
        if self.horizon not in (1, 2):
            raise ValueError("I1 frozen horizons are 1 and 2")
        if self.target_points < 0 or self.current_points < 0:
            raise ValueError("fantasy production cannot be negative")

    @property
    def persists(self) -> bool:
        return self.target_state != "out"


@dataclass(frozen=True)
class I1ForecastInput:
    position: Position
    age_band: str
    current_state: str
    horizon: int
    current_points: float
    prior_points: float | None
    experience_years: int | None
    evidence: CanonicalFootballStateEvidence | None = None


@dataclass(frozen=True)
class I1ForecastResult:
    probabilities: Mapping[str, float]
    persistence_probability: float
    anticipated_points: float
    state_means: Mapping[str, float]
    evidence_path: str
    model_version: str = I1_MODEL_VERSION


class _BinaryModel:
    def __init__(self, component: str) -> None:
        self.component = component
        self.vectorizer = DictVectorizer(sort=True)
        self.model = LogisticRegression(
            C=FROZEN_I1_REGULARIZATION.c_for(component),
            solver="lbfgs",
            max_iter=I1_MAX_ITER,
            random_state=I1_RANDOM_SEED,
        )
        self.fitted = False

    def fit(self, features: list[dict[str, object]], target: list[int]) -> None:
        counts = Counter(target)
        if (
            len(target) >= I1_MIN_TRAINING_ROWS
            and counts.get(0, 0) >= I1_MIN_BINARY_CLASS
            and counts.get(1, 0) >= I1_MIN_BINARY_CLASS
        ):
            self.model.fit(self.vectorizer.fit_transform(features), target)
            self.fitted = True

    def probability(self, features: dict[str, object]) -> float | None:
        if not self.fitted:
            return None
        return float(self.model.predict_proba(self.vectorizer.transform([features]))[0, 1])


class _OrderedPositiveStateModel:
    def __init__(self, path: str) -> None:
        names = ("useful", "starter", "premium", "elite")
        self.models = tuple(
            _BinaryModel(f"conditional.{path}.{name}")
            for name in names
        )

    def fit(self, features: list[dict[str, object]], states: list[str]) -> None:
        thresholds = (
            USEFUL_STATES,
            STARTER_STATES,
            PREMIUM_STATES,
            frozenset({"elite"}),
        )
        for model, threshold in zip(self.models, thresholds, strict=True):
            model.fit(features, [1 if state in threshold else 0 for state in states])

    def probabilities(self, features: dict[str, object]) -> dict[str, float] | None:
        cumulative: list[float] = []
        last = 1.0
        for model in self.models:
            value = model.probability(features)
            if value is None:
                return None
            value = min(last, max(0.0, min(1.0, value)))
            cumulative.append(value)
            last = value
        useful, starter, premium, elite = cumulative
        return {
            "depth": 1 - useful,
            "usable": useful - starter,
            "starter": starter - premium,
            "premium": premium - elite,
            "elite": elite,
        }


class _I1PathModel:
    def __init__(self, path: str) -> None:
        self.persistence = _BinaryModel(f"persistence.{path}")
        self.positive_states = _OrderedPositiveStateModel(path)

    def fit(self, rows: list[I1TrainingRow], *, rich: bool) -> None:
        features = [_feature_vector(row, rich=rich) for row in rows]
        self.persistence.fit(features, [1 if row.persists else 0 for row in rows])
        positive = [row for row in rows if row.persists]
        self.positive_states.fit(
            [_feature_vector(row, rich=rich) for row in positive],
            [row.target_state for row in positive],
        )

    def predict(self, item: I1ForecastInput, *, rich: bool) -> dict[str, float] | None:
        features = _feature_vector(item, rich=rich)
        persistence = self.persistence.probability(features)
        conditional = self.positive_states.probabilities(features)
        if persistence is None or conditional is None:
            return None
        result = {"out": 1 - persistence}
        result.update({state: persistence * conditional[state] for state in POSITIVE_STATES})
        total = sum(result.values())
        if total <= 0:
            return None
        return {state: value / total for state, value in result.items()}


class I1StateMeans:
    def __init__(self, rows: Iterable[I1TrainingRow]) -> None:
        self.by_position_horizon_state: dict[tuple[str, int, str], list[float]] = defaultdict(list)
        self.by_position_state: dict[tuple[str, str], list[float]] = defaultdict(list)
        self.by_horizon_state: dict[tuple[int, str], list[float]] = defaultdict(list)
        self.by_state: dict[tuple[str], list[float]] = defaultdict(list)
        for row in rows:
            position = row.position.value
            self.by_position_horizon_state[(position, row.horizon, row.target_state)].append(row.target_points)
            self.by_position_state[(position, row.target_state)].append(row.target_points)
            self.by_horizon_state[(row.horizon, row.target_state)].append(row.target_points)
            self.by_state[(row.target_state,)].append(row.target_points)

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def get(self, position: Position, horizon: int, state: str) -> float:
        candidates = (
            (self.by_position_horizon_state[(position.value, horizon, state)], 10),
            (self.by_position_state[(position.value, state)], 10),
            (self.by_horizon_state[(horizon, state)], 10),
            (self.by_state[(state,)], 5),
        )
        for values, minimum in candidates:
            if len(values) >= minimum:
                return self._mean(values)
        return 0.0

    def expected(self, probabilities: Mapping[str, float], position: Position, horizon: int) -> float:
        return sum(
            float(probabilities.get(state, 0.0)) * self.get(position, horizon, state)
            for state in STATE_NAMES
        )


class IntegratedI1Model:
    """Frozen I1 production implementation.

    The model is fit only from governed historical football outcomes. Value,
    Shapley, market and owner data are neither accepted nor referenced here.
    """

    def __init__(self, rows: Iterable[I1TrainingRow]) -> None:
        self.training_rows = tuple(rows)
        self.rich = _I1PathModel("rich")
        self.reduced = _I1PathModel("reduced")
        rich_rows = [
            row
            for row in self.training_rows
            if row.evidence is not None and row.evidence.rich_roster_evidence_available
        ]
        self.rich.fit(rich_rows, rich=True)
        self.reduced.fit(list(self.training_rows), rich=False)
        self.means = I1StateMeans(self.training_rows)

    def predict(
        self,
        item: I1ForecastInput,
        *,
        fallback_probabilities: Mapping[str, float] | None = None,
    ) -> I1ForecastResult:
        rich = item.evidence is not None and item.evidence.rich_roster_evidence_available
        path = "rich" if rich else "reduced"
        probabilities = (self.rich if rich else self.reduced).predict(item, rich=rich)
        if probabilities is None:
            if fallback_probabilities is None:
                raise ValueError("I1 model path unavailable and no governed fallback was supplied")
            probabilities = _normalize_probabilities(fallback_probabilities)
            path = "legacy_fallback"
        state_means = {
            state: max(0.0, self.means.get(item.position, item.horizon, state))
            for state in STATE_NAMES
        }
        anticipated = max(
            0.0,
            sum(probabilities[state] * state_means[state] for state in STATE_NAMES),
        )
        return I1ForecastResult(
            probabilities=probabilities,
            persistence_probability=1.0 - probabilities["out"],
            anticipated_points=anticipated,
            state_means=state_means,
            evidence_path=path,
        )


def _normalize_probabilities(probabilities: Mapping[str, float]) -> dict[str, float]:
    result = {state: max(0.0, float(probabilities.get(state, 0.0))) for state in STATE_NAMES}
    total = sum(result.values())
    if total <= 0:
        raise ValueError("career-state fallback probabilities must contain positive mass")
    return {state: value / total for state, value in result.items()}


def _feature_vector(
    row: I1TrainingRow | I1ForecastInput,
    *,
    rich: bool,
) -> dict[str, object]:
    position = row.position.value
    experience = row.experience_years
    features: dict[str, object] = {
        f"p={position}": 1,
        f"a={row.age_band}": 1,
        f"s={row.current_state}": 1,
        f"h={row.horizon}": 1,
        f"e={experience_band(experience)}": 1,
        "exp": min(15.0, max(0.0, float(experience or 0))) / 10.0,
    }

    current = max(0.0, float(row.current_points))
    prior = max(0.0, float(row.prior_points or 0.0))
    features.update(
        {
            "lp": math.log1p(current) / 6.0,
            "lprev": math.log1p(prior) / 6.0,
            "dpts": max(-2.0, min(2.0, (current - prior) / 100.0)),
            "prev_cov": 1 if row.prior_points is not None else 0,
        }
    )

    evidence = row.evidence
    role = evidence.role if evidence is not None else None
    if role is not None and evidence is not None and evidence.role_coverage:
        features.update(
            {
                f"role={role.role_band}": 1,
                "u_cov": 1,
                "lopg": math.log1p(max(0.0, role.opportunity_per_game)) / 4.0,
                "lg": math.log1p(max(0.0, role.games)) / 3.0,
            }
        )
    else:
        features.update({"role=unknown": 1, "u_cov": 0, "lopg": 0.0, "lg": 0.0})

    rich_evidence = evidence if rich else None
    if rich_evidence is None:
        features.update({"r_cov": 0, "i_cov": 0, "part_cov": 0})
        return features

    features.update(
        {
            "r_cov": 1 if rich_evidence.roster_weeks > 0 else 0,
            "i_cov": 1 if rich_evidence.injury_report_weeks > 0 else 0,
            "part_cov": 1 if rich_evidence.participation_weeks > 0 else 0,
            "active_share": rich_evidence.active_share,
            "released_share": rich_evidence.released_share,
            "practice_share": rich_evidence.practice_share,
            "reserve_share": rich_evidence.reserve_share,
            "last_status_active": float(rich_evidence.last_status_active),
            "last_status_attached": float(rich_evidence.last_status_attached),
            "last_status_release": float(rich_evidence.last_status_release),
            "last_status_practice": float(rich_evidence.last_status_practice),
            "last_status_reserve": float(rich_evidence.last_status_reserve),
            "young_active": float(row.age_band == "young") * rich_evidence.active_share,
            "low_release": float(row.current_state in {"depth", "usable"}) * rich_evidence.released_share,
            "nonir": float(rich_evidence.non_ir_injury_flag),
            "inactiveinj": float(rich_evidence.inactive_injury_flag),
            "inj_attached": float(rich_evidence.non_ir_injury_flag) * float(rich_evidence.last_status_attached),
        }
    )
    for name in (
        "status_change_count",
        "team_change_count",
        "active_return_count",
        "release_entry_count",
        "practice_entry_count",
        "reserve_entry_count",
        "injury_limited_weeks",
        "non_ir_injury_limited_weeks",
        "inactive_injury_limited_weeks",
        "reserve_injury_limited_weeks",
        "participation_weeks",
        "stats_weeks",
        "snap_play_weeks",
    ):
        features["l" + name] = math.log1p(max(0.0, float(getattr(rich_evidence, name)))) / 3.0
    return features


def feature_vector_for_validation(
    item: I1TrainingRow | I1ForecastInput,
    *,
    rich: bool,
) -> Mapping[str, object]:
    """Expose the frozen feature contract for canonical-provider parity tests."""

    return _feature_vector(item, rich=rich)
