from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from fsffl.forecast.preseason_baseline import PRESEASON_BASELINE_MODEL_VERSION
from fsffl.persistence import persistence_store_from_env
from fsffl.persistence.runtime_cache import (
    LEAGUE_SEASON_SCOPE_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    decode_preseason_forecast_baseline,
)
from fsffl.product.forecast_resilience import make_resilient_forecast_loader
from fsffl.product.runtime import default_live_forecast_loader


def _load_base_module():
    path = Path(__file__).with_name("run_private_beta_intrinsic_diagnostics.py")
    spec = importlib.util.spec_from_file_location("private_beta_intrinsic_diagnostics_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load diagnostic module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _scope_id(league_id: str, season: int) -> str:
    return f"{league_id}:{season}"


def _baseline_snapshot(store, *, league_id: str, season: int) -> dict[str, object] | None:
    if store is None:
        return None
    record = store.get_latest_reusable_artifact(
        artifact_kind=PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
        scope_kind=LEAGUE_SEASON_SCOPE_KIND,
        scope_id=_scope_id(league_id, season),
        model_version=PRESEASON_BASELINE_MODEL_VERSION,
    )
    if record is None:
        return None
    baseline = decode_preseason_forecast_baseline(dict(record.payload))
    if baseline.league_id != league_id or baseline.season != season:
        raise RuntimeError("preserved preseason baseline does not match diagnostic league-season")
    if len(set(baseline.successful_source_ids)) < 2:
        raise RuntimeError("preserved preseason baseline violates two-independent-source authority")
    return {
        "scope_id": record.key.scope_id,
        "model_version": baseline.model_version,
        "computed_at": record.computed_at.isoformat(),
        "evaluation_as_of": baseline.evaluation_as_of.isoformat(),
        "successful_source_ids": list(baseline.successful_source_ids),
        "source_count": len(set(baseline.successful_source_ids)),
        "raw_ensemble_rows": len(baseline.raw_ensemble),
        "invalidated_at": record.invalidated_at.isoformat() if record.invalidated_at else None,
    }


def _retarget_state(base, league_id: str):
    original = base._build_diagnostic_state

    def build(facts, sleeper_players):
        state, raw_status, source_by_player = original(facts, sleeper_players)
        league = state.league.model_copy(
            update={
                "league_id": league_id,
                "name": "FSFFL NEXT management validation fixture using hosted league-season authority",
            }
        )
        teams = tuple(team.model_copy(update={"league_id": league_id}) for team in state.teams)
        return state.model_copy(update={"league": league, "teams": teams}), raw_status, source_by_player

    base._build_diagnostic_state = build


def _provider_only_report(base, output_json: Path, output_md: Path, *, league_id: str | None) -> None:
    facts_raw = json.loads(base.activation_artifact_text("current_i1_facts_2026.json"))
    facts = base.CurrentI1FactsArtifact.from_dict(facts_raw)
    sleeper_players = base._load_sleeper_players()
    state, _, _ = base._build_diagnostic_state(facts, sleeper_players)
    started = time.perf_counter()
    try:
        evidence = default_live_forecast_loader(state)
        provider_health = {
            "status": "AVAILABLE",
            "successful_source_ids": list(evidence.successful_source_ids),
            "failed_sources": list(evidence.failed_sources),
            "error": None,
        }
    except Exception as exc:
        provider_health = {
            "status": "DEGRADED",
            "successful_source_ids": [],
            "failed_sources": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    elapsed = time.perf_counter() - started
    report = {
        "status": "PROVIDER_HEALTH_ONLY",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "management diagnostic only; raw provider health is not governed Forecast availability",
        "provider_health": {**provider_health, "probe_seconds": elapsed},
        "governed_forecast": {
            "evaluated": False,
            "reason": (
                "This runner has no FSFFL_DATABASE_URL and therefore cannot exercise the hosted "
                "make_resilient_forecast_loader persistence path. Provider health is reported "
                "separately and must not be treated as Forecast unavailability."
            ),
            "league_id_configured": bool(league_id),
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(
        "\n".join(
            [
                "# FSFFL NEXT private-beta Intrinsic provider-health diagnostic",
                "",
                "Status: **PROVIDER_HEALTH_ONLY**",
                "",
                "Raw provider availability is operational evidence only. It is not the governed Forecast availability result.",
                "",
                f"- Provider probe: `{provider_health['status']}`.",
                f"- Successful live sources: {', '.join(provider_health['successful_source_ids']) or 'none'}.",
                f"- Provider error: {provider_health['error'] or 'none'}.",
                "- Governed Forecast was not evaluated because this runner has no production persistence connection.",
                "- The final authority test must run through `make_resilient_forecast_loader` against the preserved league-season baseline.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _augment_live_sanity_without_persistence(
    base,
    output_json: Path,
    output_md: Path,
    *,
    league_id: str | None,
) -> None:
    """Keep the player sanity/display evidence visible when Actions lacks DB access.

    This is deliberately not promoted to governed Forecast authority. The base
    diagnostic still enforces the normal two-independent-source live Forecast gate,
    exercises the Shapley-native endpoint, and produces the full player sanity board.
    The report then records that persistence-backed resilience remains a separate
    authority check rather than hiding the useful candidate diagnostics.
    """

    base.run(output_json, output_md)
    report = json.loads(output_json.read_text(encoding="utf-8"))
    live = report.get("live_forecast", {})
    successful = list(live.get("successful_sources", [])) if isinstance(live, dict) else []
    failed = list(live.get("failed_sources", [])) if isinstance(live, dict) else []
    report["status"] = "LIVE_SANITY_PASS_PERSISTENCE_AUTHORITY_PENDING"
    report["provider_health"] = {
        "status": "AVAILABLE",
        "successful_source_ids": successful,
        "failed_sources": failed,
        "error": None,
        "probe_seconds": live.get("forecast_acquisition_seconds") if isinstance(live, dict) else None,
    }
    report["governed_forecast"] = {
        "evaluated": False,
        "reason": (
            "The full sanity board and endpoint smoke used the governed two-source live Forecast path, "
            "but this GitHub runner has no FSFFL_DATABASE_URL and therefore did not exercise the "
            "hosted make_resilient_forecast_loader persistence fallback."
        ),
        "league_id_configured": bool(league_id),
        "sanity_board_basis": "direct_live_two_source_forecast",
    }
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output_md.open("a", encoding="utf-8") as handle:
        handle.write("\n## Persistence authority note\n\n")
        handle.write("The player sanity board and endpoint smoke above used valid two-source live Forecast evidence.\n\n")
        handle.write("This GitHub runner does not have `FSFFL_DATABASE_URL`, so it did not prove the hosted persistence-backed fallback in this run. That authority check remains separate and must not be inferred from provider health alone.\n")


def run(
    output_json: Path,
    output_md: Path,
    *,
    league_id: str | None,
    allow_provider_only: bool,
) -> None:
    base = _load_base_module()
    store = persistence_store_from_env()
    configured_league_id = (league_id or os.getenv("FSFFL_DIAGNOSTIC_LEAGUE_ID", "")).strip() or None

    if store is None or configured_league_id is None:
        if not allow_provider_only:
            missing = []
            if store is None:
                missing.append("FSFFL_DATABASE_URL")
            if configured_league_id is None:
                missing.append("FSFFL_DIAGNOSTIC_LEAGUE_ID/--league-id")
            raise RuntimeError(
                "governed Forecast diagnostic requires hosted persistence context; missing "
                + ", ".join(missing)
            )
        _provider_only_report(base, output_json, output_md, league_id=configured_league_id)
        provider_report = json.loads(output_json.read_text(encoding="utf-8"))
        provider_health = provider_report.get("provider_health", {})
        if isinstance(provider_health, dict) and provider_health.get("status") == "AVAILABLE":
            _augment_live_sanity_without_persistence(
                base,
                output_json,
                output_md,
                league_id=configured_league_id,
            )
        return

    _retarget_state(base, configured_league_id)
    baseline = _baseline_snapshot(store, league_id=configured_league_id, season=2026)
    if baseline is None:
        raise RuntimeError(
            "authoritative 2026 preseason baseline is missing from persistence for "
            f"{configured_league_id}; this is a concrete Forecast-resilience integration defect"
        )

    provider_health: dict[str, object] = {}
    governed: dict[str, object] = {}

    def live_probe(state):
        started = time.perf_counter()
        try:
            evidence = default_live_forecast_loader(state)
        except Exception as exc:
            provider_health.update(
                {
                    "status": "DEGRADED",
                    "successful_source_ids": [],
                    "failed_sources": [],
                    "error": f"{type(exc).__name__}: {exc}",
                    "probe_seconds": time.perf_counter() - started,
                }
            )
            raise
        provider_health.update(
            {
                "status": "AVAILABLE",
                "successful_source_ids": list(evidence.successful_source_ids),
                "failed_sources": list(evidence.failed_sources),
                "error": None,
                "probe_seconds": time.perf_counter() - started,
            }
        )
        return evidence

    resilient = make_resilient_forecast_loader(store, live_loader=live_probe)

    def authoritative_loader(state):
        started = time.perf_counter()
        evidence = resilient(state)
        governed.update(
            {
                "evaluated": True,
                "evidence_basis": evidence.evidence_basis,
                "successful_source_ids": list(evidence.successful_source_ids),
                "failed_sources": list(evidence.failed_sources),
                "acquisition_seconds": time.perf_counter() - started,
            }
        )
        return evidence

    # The legacy diagnostic helper is retained for its coverage/sanity/latency board,
    # but its Forecast dependency is replaced with the exact hosted resilient authority.
    base.default_live_forecast_loader = authoritative_loader
    base.run(output_json, output_md)

    report = json.loads(output_json.read_text(encoding="utf-8"))
    report["provider_health"] = provider_health
    report["governed_forecast"] = governed
    report["preseason_baseline"] = baseline
    report["forecast_authority"] = "make_resilient_forecast_loader"
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with output_md.open("a", encoding="utf-8") as handle:
        handle.write("\n## Forecast resilience reconciliation\n\n")
        handle.write("The sanity/coverage/latency board above used the same `make_resilient_forecast_loader` authority as the hosted persistent app.\n\n")
        handle.write(f"- Governed evidence basis: `{governed.get('evidence_basis')}`.\n")
        handle.write(f"- Preserved baseline sources: {', '.join(baseline['successful_source_ids'])}.\n")
        handle.write(f"- Preserved baseline observations: {baseline['raw_ensemble_rows']}.\n")
        handle.write(f"- Current raw-provider health: `{provider_health.get('status', 'unknown')}`.\n")
        if provider_health.get("error"):
            handle.write(f"- Raw-provider error: {provider_health['error']}\n")
        handle.write("- Raw provider health is reported separately and does not override governed Forecast availability when a valid preserved baseline is used.\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--league-id")
    parser.add_argument(
        "--allow-provider-only",
        action="store_true",
        help="Emit a non-authoritative provider-health report when hosted persistence is unavailable.",
    )
    args = parser.parse_args()
    run(
        args.output_json,
        args.output_md,
        league_id=args.league_id,
        allow_provider_only=args.allow_provider_only,
    )


if __name__ == "__main__":
    main()
