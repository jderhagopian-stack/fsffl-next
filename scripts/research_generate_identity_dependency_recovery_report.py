from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/research/production_resolution/FSFFL_NEXT_Identity_Materialization_Dependency_Recovery_Report.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#245B78")
PALE = colors.HexColor("#EAF1F5")
RED = colors.HexColor("#9E2A2B")
GRAY = colors.HexColor("#4C5963")

pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Title2", parent=styles["Title"], fontName="DejaVu-Bold", fontSize=22, leading=27, textColor=NAVY, alignment=TA_CENTER, spaceAfter=14))
styles.add(ParagraphStyle(name="Sub", parent=styles["Normal"], fontName="DejaVu", fontSize=10.5, leading=15, textColor=GRAY, alignment=TA_CENTER, spaceAfter=18))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="DejaVu-Bold", fontSize=15, leading=18, textColor=NAVY, spaceBefore=8, spaceAfter=8))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="DejaVu-Bold", fontSize=11.5, leading=14, textColor=BLUE, spaceBefore=7, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="DejaVu", fontSize=9.2, leading=13, textColor=colors.HexColor("#202A32"), spaceAfter=7))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="DejaVu", fontSize=7.6, leading=10, textColor=colors.HexColor("#26333C")))
styles.add(ParagraphStyle(name="Stop", parent=styles["BodyText"], fontName="DejaVu-Bold", fontSize=10.2, leading=14, textColor=RED, borderColor=RED, borderWidth=0.8, borderPadding=8, backColor=colors.HexColor("#FCEBEC"), spaceBefore=10, spaceAfter=8))


def p(text, style="Bodyx"):
    return Paragraph(text, styles[style])


def table(data, widths, header=True, small=False):
    cooked = [[p(str(c), "Smallx" if small else "Bodyx") for c in row] for row in data]
    t = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    rules = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C5CE")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        rules += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    for i in range(1 if header else 0, len(data)):
        if i % 2 == 0:
            rules.append(("BACKGROUND", (0, i), (-1, i), PALE))
    t.setStyle(TableStyle(rules))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#C6D1D8"))
    canvas.line(0.7 * inch, 0.55 * inch, 7.8 * inch, 0.55 * inch)
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.7 * inch, 0.36 * inch, "FSFFL NEXT • research-only recovery checkpoint • 2026-09-18")
    canvas.drawRightString(7.8 * inch, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = [
    Spacer(1, 0.3 * inch),
    p("FSFFL NEXT", "Title2"),
    p("Frozen Identity / Materialization Dependency Recovery", "Title2"),
    p("Management checkpoint • exact recovery only • 18 September 2026", "Sub"),
    p("BOUNDED NEGATIVE RESULT — STOP", "Stop"),
    p("The frozen selected-candidate training procedure and fitted parameters were recovered exactly. The original 335-row current-player → historical identity bridge and exact 2024/2023 PIT residual inputs were not persisted and cannot be reproduced without a new methodological choice."),
    Spacer(1, 8),
    table([
        ["Boundary", "Finding"],
        ["Frozen fit", "Recovered exactly; no refit or reselection"],
        ["Current identity bridge", "Not persisted; constructed in memory from contemporaneous provider data"],
        ["335-player direct GSIS coverage", "73 present / 262 absent"],
        ["Required action", "Governance decision for a replacement coordinate; not a recovery step"],
    ], [2.0 * inch, 4.85 * inch]),
    p("What was recovered", "H1x"),
    p("Candidate: fixed routed Forecast + M1a + two-prior-season consistency. QB uses A2+C+D; RB/WR/TE use A2+D. Only positive-state conditional-production means change; persistence and state probabilities remain frozen."),
    p("Training and feature procedure", "H2x"),
    p("Eligible training rows are positive source/target transitions satisfying source_season + horizon ≤ evaluation cutoff. Historical source seasons end in 2022. M1a is BayesianRidge(fit_intercept=False) on target versus current within-state residual z. The consistency fit predicts the residual remaining after M1a from two genuine prior seasons only; covered values use training-only population moments (ddof=0)."),
    table([
        ["Exact fitted item", "Y2", "Y3"],
        ["Training rows", "5,974", "4,781"],
        ["Source seasons", "2005–2022", "2005–2022"],
        ["M1a coefficient", "0.07939942531895901", "0.07812314495946265"],
        ["Prior-two coverage", "0.5033478406427854", "0.4862999372516210"],
        ["Mean μ / σ", "0.1805173562 / 0.8250069242", "0.2161366754 / 0.8286552915"],
        ["Gap μ / σ", "1.1093450525 / 0.9101986765", "1.1049215895 / 0.8918729700"],
    ], [2.15 * inch, 2.35 * inch, 2.35 * inch], small=True),
    PageBreak(),
    p("Exact consistency coefficients", "H1x"),
    p("Order: mean_global, gap_global, coverage_global, then mean/gap position deviations for QB, RB, WR, TE."),
    table([
        ["Term", "Y2", "Y3"],
        ["mean_global", "0.104407393", "0.0896474572"],
        ["gap_global", "0.0256567937", "0.00230448058"],
        ["coverage_global", "0.026386248", "0.0208369151"],
        ["mean_dev_QB", "0.158161626", "0.180179816"],
        ["gap_dev_QB", "−0.0501651272", "−0.057293661"],
        ["mean_dev_RB", "−0.00347923962", "−0.00910620769"],
        ["gap_dev_RB", "−0.000109866463", "−0.0241324898"],
        ["mean_dev_WR", "0.0189868866", "0.0336007196"],
        ["gap_dev_WR", "−0.0249518009", "−0.0225647051"],
        ["mean_dev_TE", "−0.0206613761", "−0.00887356736"],
        ["gap_dev_TE", "0.0522830842", "0.000142033387"],
    ], [2.15 * inch, 2.35 * inch, 2.35 * inch], small=True),
    p("These values were copied from the frozen final diagnostic. They were not re-estimated in this recovery.", "Smallx"),
    p("Search coverage", "H1x"),
    table([
        ["Surface", "Bounded search", "Result"],
        ["Git", "179 refs; 2,583 commits; stashes; reflogs; unreachable objects", "No bridge/materializer/table"],
        ["Repository", "Phase2, Phase34, production-resolution, activation artifacts and path history", "Fit recovered; resolved identities absent"],
        ["Actions", "Activation run 35145456513; Year-1 run 35330898624; artifacts and logs", "Exact ZIPs recovered; ephemeral bridge/cache not uploaded"],
        ["Local remnants", "/workspace/scratch, /mnt, /tmp, all worktrees", "Older routed runner and Phase2 archive only"],
    ], [1.15 * inch, 3.0 * inch, 2.7 * inch], small=True),
    p("Actions evidence", "H2x"),
    p("The activation ZIP exactly matches SHA-256 3866d653…95ca5 and contains only current_i1_facts_2026.json, frozen_i1_h12.json, frozen_i1_h3.json, and the build report. Logs show /tmp/private_beta_completed_source_points.csv, /tmp/nflreadpy-cache, and an in-memory stable-ID bridge. The upload step excluded all three; the workflow used no actions/cache persistence step."),
    PageBreak(),
    p("Missing reproducibility dependency", "H1x"),
    p("Exact materialization requires the original frozen 335-row Sleeper → historical player/source-key crosswalk plus the corresponding exact 2024 and 2023 PIT age/state residual inputs, or a row-complete 335-player table already containing them."),
    p("Why the boundary cannot be crossed", "H2x"),
    p("The activation builder resolved identities from contemporaneous nflreadpy player/2025-roster snapshots and Sleeper data using a unique name+position bridge. Output rows retain Sleeper IDs and aggregate bridge counts—not the resolved historical keys. The exact provider snapshots were not preserved. Running the same code today would resolve against different evidence and could change collision or unmatched outcomes."),
    table([
        ["Dependency", "Classification"],
        ["Historical cutoff procedure", "Recovered exact"],
        ["Frozen fitted parameters", "Recovered exact"],
        ["Later 335-player Year-1 universe", "Recovered exact; fresh later coordinate"],
        ["Original row-level identity bridge", "Not persisted"],
        ["Exact 2024/2023 PIT inputs", "Not persisted"],
        ["Ephemeral runner files/snapshots", "Destroyed or inaccessible; equivalence unproven"],
        ["Exact current-player materialization", "Not reproducible without new methodology"],
    ], [2.65 * inch, 4.2 * inch], small=True),
    p("Sentinel evidence", "H2x"),
    p("Direct GSIS references exist for Aaron Rodgers, Sam Darnold, and Christian McCaffrey. They are absent for Bijan Robinson, Jahmyr Gibbs, Puka Nacua, Brock Bowers, and Trey McBride. This proves the missing bridge affects five of the eight named sentinels and 262 of 335 governed rows."),
    p("Minimum governance decision", "H1x"),
    p("Authorize a replacement identity/materialization coordinate: name and version the provider snapshot; predeclare collision and unmatched-player rules; persist the full 335-row crosswalk and exact 2024/2023 PIT inputs. That would be a new evidence coordinate and must not be described as recovery of the frozen original."),
    p("STOP. Do not substitute another training window, refit, rebuild identities heuristically, fetch fresh provider data, materialize Y2/Y3, run sentinel parity, or run Shapley under this authority.", "Stop"),
]

doc = SimpleDocTemplate(str(OUT), pagesize=letter, rightMargin=0.7 * inch, leftMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.75 * inch, title="FSFFL NEXT Identity Materialization Dependency Recovery", author="OpenAI Codex")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
