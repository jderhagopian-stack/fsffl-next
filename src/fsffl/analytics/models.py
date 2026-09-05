from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel


class AnalyticsWarningKind(StrEnum):
    MISSING_EVIDENCE = "missing_evidence"
    PROVISIONAL = "provisional"
    UNKNOWN_ACCEPTANCE = "unknown_acceptance"
    SEARCH_TRUNCATED = "search_truncated"
    SEARCH_NOT_EXHAUSTED = "search_not_exhausted"
    POLICY_NOT_SUPPLIED = "policy_not_supplied"
    OTHER = "other"


class AnalyticsWarning(FrozenModel):
    kind: AnalyticsWarningKind
    code: str
    message: str
    source_component: str | None = None

    @model_validator(mode="after")
    def validate_warning(self) -> "AnalyticsWarning":
        if not self.code.strip() or not self.message.strip():
            raise ValueError("analytics warning code/message cannot be blank")
        if self.source_component is not None and not self.source_component.strip():
            raise ValueError("source_component cannot be blank")
        return self


class ModelLineageEntry(FrozenModel):
    component: str
    model_version: str

    @model_validator(mode="after")
    def validate_lineage(self) -> "ModelLineageEntry":
        if not self.component.strip() or not self.model_version.strip():
            raise ValueError("lineage component/version cannot be blank")
        return self


class AnalyticsContext(FrozenModel):
    """Reproducible identity/provenance carried by every NEXT-7 response."""

    schema_version: str
    league_id: str
    league_state_id: str
    as_of: datetime
    generated_at: datetime
    lineage: tuple[ModelLineageEntry, ...]
    warnings: tuple[AnalyticsWarning, ...] = ()

    @field_validator("as_of", "generated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("analytics timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_context(self) -> "AnalyticsContext":
        if any(not value.strip() for value in (
            self.schema_version,
            self.league_id,
            self.league_state_id,
        )):
            raise ValueError("analytics context identifiers cannot be blank")
        components = [entry.component for entry in self.lineage]
        if len(components) != len(set(components)):
            raise ValueError("analytics lineage may contain one version per component")
        warning_keys = [(warning.kind, warning.code) for warning in self.warnings]
        if len(warning_keys) != len(set(warning_keys)):
            raise ValueError("duplicate analytics warnings are not allowed")
        if self.generated_at < self.as_of:
            raise ValueError("analytics generated_at cannot precede evidence as_of")
        return self


def canonical_analytics_json(model: FrozenModel) -> str:
    """Stable JSON encoding for reproducible API/report payloads."""

    return json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
