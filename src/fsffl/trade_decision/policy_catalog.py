from __future__ import annotations

from datetime import UTC, datetime

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.value.cardinal_authority import FSFFL_CARDINAL_SCALE, FSFFL_CARDINAL_VALIDATION_MAE

from .materiality import CompetitiveMaterialityPolicy, EconomicMaterialityPolicy


_POLICY_EVIDENCE_THROUGH = datetime(2026, 9, 1, tzinfo=UTC)


class MaterialityPolicyBundle(FrozenModel):
    """Versioned Decision policy bundle with explicit provisional status.

    These are practical-significance tolerances, not claims that every delta below
    them is literally zero. The bundle is intentionally provisional and is designed
    to be replaced by evidence-updating calibration without changing disposition
    architecture.
    """

    competitive: CompetitiveMaterialityPolicy
    economic: EconomicMaterialityPolicy
    authority_status: str = "bounded_provisional_prior"
    update_mode: str = "evidence_updating"
    model_version: str = "next5-live-materiality-bundle-v1"

    @model_validator(mode="after")
    def validate_bundle(self) -> "MaterialityPolicyBundle":
        if self.authority_status != "bounded_provisional_prior":
            raise ValueError("live materiality v1 must remain explicitly provisional")
        if self.update_mode != "evidence_updating":
            raise ValueError("live materiality v1 must remain evidence-updating")
        if not self.model_version.strip():
            raise ValueError("materiality bundle model_version cannot be blank")
        return self


def live_bounded_materiality_policy(*, as_of: datetime) -> MaterialityPolicyBundle:
    """Return the governed private-beta materiality policy when PIT-safe.

    Competitive tolerances are bounded practical-significance priors chosen for the
    private beta and must be recalibrated from reconstructed trade decisions. The
    economic tolerance is anchored directly to the current cardinal cross-source
    holdout MAE rather than a hidden round-number coefficient.
    """

    if as_of.tzinfo is None:
        raise ValueError("materiality policy request must be timezone-aware")
    if as_of < _POLICY_EVIDENCE_THROUGH:
        raise ValueError("live materiality policy is unavailable before its evidence cutoff")

    competitive = CompetitiveMaterialityPolicy(
        expected_wins_abs=0.20,
        playoff_probability_abs=0.02,
        first_place_probability_abs=0.02,
        championship_probability_abs=0.01,
        lineup_drop_abs=2.0,
        model_version="next5-competitive-materiality-provisional-v1",
        evidence_through=_POLICY_EVIDENCE_THROUGH,
        provenance=(
            "bounded provisional practical-significance prior for private-beta action testing; "
            "expected wins 0.20, playoff odds 2 percentage points, championship odds 1 percentage point, "
            "and single-player lineup-loss exposure 2 fantasy points; evidence-updating replacement required"
        ),
    )
    economic = EconomicMaterialityPolicy(
        scale=FSFFL_CARDINAL_SCALE,
        mean_value_abs=FSFFL_CARDINAL_VALIDATION_MAE,
        model_version="next5-economic-materiality-cardinal-holdout-mae-v1",
        evidence_through=_POLICY_EVIDENCE_THROUGH,
        provenance=(
            "FSFFL cardinal cross-source holdout MAE used as the current market-value noise floor; "
            "replace with transaction-calibrated materiality as package evidence matures"
        ),
    )
    return MaterialityPolicyBundle(competitive=competitive, economic=economic)
