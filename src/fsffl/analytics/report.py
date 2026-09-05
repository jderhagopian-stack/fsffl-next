from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .league import LeagueAnalyticsView, LeagueMetricRanking
from .models import AnalyticsContext
from .opportunity import OpportunityAnalyticsView, TradePartnerAnalyticsView
from .team import TeamAnalyticsView


class LeagueReportData(FrozenModel):
    """Report-ready composition of existing NEXT-7 views; no new model logic."""

    context: AnalyticsContext
    title: str
    league: LeagueAnalyticsView
    teams: tuple[TeamAnalyticsView, ...]
    rankings: tuple[LeagueMetricRanking, ...] = ()
    opportunities: OpportunityAnalyticsView | None = None
    trade_partners: TradePartnerAnalyticsView | None = None
    report_model_version: str = "next7-league-report-v1"

    @model_validator(mode="after")
    def validate_report(self) -> "LeagueReportData":
        if not self.title.strip() or not self.report_model_version.strip():
            raise ValueError("report identifiers cannot be blank")
        if self.league.context != self.context:
            raise ValueError("league report view must share report context")
        if any(team.context != self.context for team in self.teams):
            raise ValueError("all team report views must share report context")
        if self.opportunities is not None and self.opportunities.context != self.context:
            raise ValueError("opportunity report view must share report context")
        if self.trade_partners is not None and self.trade_partners.context != self.context:
            raise ValueError("trade partner report view must share report context")
        return self


def _fmt(value: float | int | str | None, *, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def render_league_report_markdown(report: LeagueReportData) -> str:
    """Deterministic static report renderer containing presentation logic only."""

    lines: list[str] = [f"# {report.title}", ""]
    lines.append(f"**League:** {report.context.league_id}")
    lines.append(f"**As of:** {report.context.as_of.isoformat()}")
    lines.append(f"**State:** `{report.context.league_state_id}`")
    lines.append("")

    if report.context.warnings:
        lines.extend(["## Important model notes", ""])
        for warning in report.context.warnings:
            lines.append(f"- **{warning.kind.value}:** {warning.message}")
        lines.append("")

    lines.extend([
        "## League snapshot",
        "",
        "| Team | Projected points | Expected wins | Playoff odds | First-place odds | Dynasty portfolio | Picks |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in report.league.teams:
        lines.append(
            "| "
            + " | ".join(
                (
                    row.display_name,
                    _fmt(row.optimized_expected_points),
                    _fmt(row.expected_wins),
                    _pct(row.playoff_probability),
                    _pct(row.first_place_probability),
                    _fmt(row.asset_portfolio_mean),
                    str(row.draft_pick_count),
                )
            )
            + " |"
        )
    lines.append("")

    if report.rankings:
        lines.extend(["## Explicit metric rankings", ""])
        for ranking in report.rankings:
            lines.append(f"### {ranking.metric.value.replace('_', ' ').title()}")
            lines.append("")
            lines.append("| Rank | Team | Value |")
            lines.append("| ---: | --- | ---: |")
            for row in ranking.rows:
                lines.append(f"| {row.rank} | {row.display_name} | {_fmt(row.value)} |")
            if ranking.missing_team_ids:
                lines.append("")
                lines.append("Missing evidence: " + ", ".join(ranking.missing_team_ids))
            lines.append("")

    if report.opportunities is not None:
        summary = report.opportunities.authority_summary
        lines.extend([
            "## Opportunity search",
            "",
            f"- Actionable: **{summary.actionable}**",
            f"- Market-test only: **{summary.market_test_only}**",
            f"- Diagnostic only: **{summary.diagnostic_only}**",
            f"- No action authority: **{summary.none}**",
            "",
        ])
        if report.opportunities.reason_counts:
            lines.append("Common limitations / blockers:")
            for item in report.opportunities.reason_counts:
                lines.append(f"- {item.reason.value.replace('_', ' ')}: {item.count}")
            lines.append("")

    if report.trade_partners is not None:
        lines.extend([
            "## Trade partner intelligence",
            "",
            "| Counterparty | Evaluated | Actionable | Market-test | Pareto | Mutual-gain candidates | Acceptance unknown |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for row in report.trade_partners.partners:
            lines.append(
                f"| {row.counterparty_team_id} | {row.evaluated_candidates} | "
                f"{row.actionable_candidates} | {row.market_test_candidates} | "
                f"{row.pareto_candidates} | {row.mutual_gain_candidates} | "
                f"{row.acceptance_unknown_candidates} |"
            )
        lines.append("")

    lines.append("## Team rosters")
    lines.append("")
    for team in sorted(report.teams, key=lambda item: item.team_id):
        lines.append(f"### {team.display_name}")
        lines.append("")
        lines.append("| Player | Pos | Roster | Projected role | Age |")
        lines.append("| --- | --- | --- | --- | ---: |")
        for player in team.players:
            role = (
                player.projected_lineup_slot.value
                if player.projected_starter and player.projected_lineup_slot is not None
                else player.roster_slot.value
            )
            lines.append(
                f"| {player.full_name} | {player.position.value} | {player.roster_slot.value} | "
                f"{role} | {_fmt(player.age_years, digits=1)} |"
            )
        lines.append("")

    lines.extend([
        "## Model lineage",
        "",
        "| Component | Version |",
        "| --- | --- |",
    ])
    for item in report.context.lineage:
        lines.append(f"| {item.component} | {item.model_version} |")
    lines.append("")
    return "\n".join(lines)
