from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/research/production_resolution/replacement_identity_materialization_v1_20260918T170621Z/FSFFL_NEXT_Replacement_Identity_Materialization_Coordinate_Report.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#245B78")
PALE = colors.HexColor("#EAF1F5")
GREEN = colors.HexColor("#1F6B4F")
RED = colors.HexColor("#9E2A2B")
GRAY = colors.HexColor("#4C5963")

pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="DejaVu-Bold", fontSize=21, leading=26, textColor=NAVY, alignment=TA_CENTER, spaceAfter=12))
styles.add(ParagraphStyle(name="SubX", parent=styles["Normal"], fontName="DejaVu", fontSize=10.2, leading=14, textColor=GRAY, alignment=TA_CENTER, spaceAfter=16))
styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontName="DejaVu-Bold", fontSize=15, leading=18, textColor=NAVY, spaceBefore=7, spaceAfter=7))
styles.add(ParagraphStyle(name="H2X", parent=styles["Heading2"], fontName="DejaVu-Bold", fontSize=11.5, leading=14, textColor=BLUE, spaceBefore=6, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontName="DejaVu", fontSize=9.1, leading=13, textColor=colors.HexColor("#202A32"), spaceAfter=6))
styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontName="DejaVu", fontSize=7.5, leading=9.5, textColor=colors.HexColor("#26333C")))
styles.add(ParagraphStyle(name="PassX", parent=styles["BodyText"], fontName="DejaVu-Bold", fontSize=10, leading=14, textColor=GREEN, borderColor=GREEN, borderWidth=0.8, borderPadding=8, backColor=colors.HexColor("#EAF7F1"), spaceAfter=8))
styles.add(ParagraphStyle(name="StopX", parent=styles["BodyText"], fontName="DejaVu-Bold", fontSize=9.8, leading=14, textColor=RED, borderColor=RED, borderWidth=0.8, borderPadding=8, backColor=colors.HexColor("#FCEBEC"), spaceBefore=8))


def p(text: str, style: str = "BodyX") -> Paragraph:
    return Paragraph(text, styles[style])


def table(data, widths, small=False):
    cells = [[p(str(cell), "SmallX" if small else "BodyX") for cell in row] for row in data]
    result = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C5CE")),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for index in range(2, len(data), 2):
        commands.append(("BACKGROUND", (0, index), (-1, index), PALE))
    result.setStyle(TableStyle(commands))
    return result


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#C6D1D8"))
    canvas.line(0.7 * inch, 0.55 * inch, 7.8 * inch, 0.55 * inch)
    canvas.setFont("DejaVu", 7.3)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.7 * inch, 0.36 * inch, "FSFFL NEXT - new replacement evidence coordinate - 2026-09-18")
    canvas.drawRightString(7.8 * inch, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = [
    Spacer(1, 0.25 * inch),
    p("FSFFL NEXT", "TitleX"),
    p("Replacement Identity / Materialization Coordinate", "TitleX"),
    p("New governed evidence coordinate - data engineering only", "SubX"),
    p("PASS - 335 ROWS CONSTRUCTED, HASHED, RELOADED, AND AUDITED", "PassX"),
    p("This is a new replacement coordinate created after exact recovery of the original bridge failed. It is not the recovered original. The frozen routed + M1a + two-prior-season Forecast remains unchanged and was not executed."),
    table([
        ["Gate", "Result"],
        ["Frozen population", "335/335 exact Year-1 row identities"],
        ["Deterministic identity", "300 matched; 35 unmatched; 0 ambiguous"],
        ["Accepted-ID uniqueness", "300 unique GSIS IDs; no collisions"],
        ["Two-prior PIT coverage", "199 covered; explicit reason on every uncovered row"],
        ["Fresh-read reload", "PASS - identical row and population hashes"],
    ], [2.2 * inch, 4.65 * inch]),
    p("Coordinate result", "H1X"),
    table([
        ["Mapping status", "Rows", "Meaning"],
        ["DIRECT_ID", "73", "Existing Year-1 GSIS validated against provider identity"],
        ["CANONICAL_CROSSID", "0", "No qualifying pre-task repository cross-ID source existed"],
        ["EXACT_NAME_POSITION", "227", "Reverse-unique exact normalized name + compatible position"],
        ["AMBIGUOUS", "0", "No tie was manually resolved"],
        ["UNMATCHED", "35", "Retained explicitly; no exact provider candidate"],
    ], [2.0 * inch, 0.8 * inch, 4.05 * inch], small=True),
    p("Row-material SHA-256", "H2X"),
    p("<font name='DejaVu'>1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56</font>", "SmallX"),
    p("PIT coverage", "H1X"),
    table([
        ["Status", "Rows"],
        ["Two genuine prior seasons", "199"],
        ["Missing 2023 only", "46"],
        ["Missing 2024 only", "1"],
        ["No 2024 or 2023 history", "54"],
        ["Identity unmatched", "35"],
    ], [4.9 * inch, 1.95 * inch]),
    PageBreak(),
    p("Frozen rules and evidence", "H1X"),
    p("Identity rule order was fixed before output inspection: validated existing GSIS; qualifying pre-task repository canonical cross-ID; then exact normalized name + compatible position. Exact-name acceptance required one provider candidate, reverse uniqueness on the current side, and no accepted GSIS collision."),
    p("Forbidden tie-breaks were not used", "H2X"),
    p("No fuzzy-name score, production similarity, age/experience similarity, fantasy points, current ranking, sentinel status, manual preference, Forecast output, or Shapley output resolved any identity."),
    p("Frozen provider coordinate", "H2X"),
    table([
        ["Source", "Asset / timestamp", "SHA-256"],
        ["NFLverse players.csv", "Asset 572597132; updated 2026-09-18 12:34:30Z", "801d5fec...59b579b6"],
        ["NFLverse roster_2025.csv", "Asset 373640814; updated 2026-03-14 07:33:08Z", "531ee5de...fb4d04ad"],
        ["Governed identity subset", "916 roster-limited skill-player records", "Full hash in manifest"],
    ], [1.8 * inch, 3.1 * inch, 1.95 * inch], small=True),
    p("Raw upstream files are not redistributed. The exact governed identity fields used by the matcher are persisted with source URLs, asset IDs, timestamps, and raw hashes."),
    p("Identity validation", "H2X"),
    p("All 73 direct IDs passed name and position validation. All 227 exact-name matches had exactly one provider candidate. Accepted GSIS IDs are unique. As an independent post-hoc check only, the provider's Sleeper cross-ID agreed for 300/300 accepted matches with zero disagreements; it was not used to accept matches."),
    p("Frozen PIT methodology", "H1X"),
    p("The 2023 age/state residual uses only seasons before 2023; the 2024 residual uses only seasons before 2024. Position/state and position/age-band/state reference cells use the already-frozen fallback and support rules. No selected-Forecast parameter was estimated."),
    table([
        ["Parity gate", "Result"],
        ["Persisted 2022 rows compared", "619/619"],
        ["Maximum residual-z difference", "4.440892098500626e-16"],
        ["Residual-scope mismatches", "0"],
        ["Missing rebuilt rows", "0"],
        ["Status", "PASS"],
    ], [3.7 * inch, 3.15 * inch]),
    p("No-history handling", "H2X"),
    p("A mapped player without both genuine seasons receives neutral continuous inputs with prior2_coverage=0 and a specific missing-history reason. An unmatched identity remains IDENTITY_UNMATCHED and is never silently converted into ordinary no-history."),
    PageBreak(),
    p("Eight-sentinel identity audit", "H1X"),
    p("Identity and history availability only - no sentinel Forecast was computed or compared."),
    table([
        ["Sentinel", "Mapping", "GSIS", "2024", "2023", "Prior-two"],
        ["Aaron Rodgers", "DIRECT_ID", "00-0023459", "Yes", "Yes", "Covered"],
        ["Sam Darnold", "DIRECT_ID", "00-0034869", "Yes", "Yes", "Covered"],
        ["Bijan Robinson", "EXACT_NAME_POSITION", "00-0038542", "Yes", "Yes", "Covered"],
        ["Jahmyr Gibbs", "EXACT_NAME_POSITION", "00-0039139", "Yes", "Yes", "Covered"],
        ["Puka Nacua", "EXACT_NAME_POSITION", "00-0039075", "Yes", "Yes", "Covered"],
        ["Christian McCaffrey", "DIRECT_ID", "00-0033280", "Yes", "Yes", "Covered"],
        ["Brock Bowers", "EXACT_NAME_POSITION", "00-0039338", "Yes", "No", "Missing 2023"],
        ["Trey McBride", "EXACT_NAME_POSITION", "00-0037744", "Yes", "Yes", "Covered"],
    ], [1.35 * inch, 1.55 * inch, 1.05 * inch, 0.55 * inch, 0.55 * inch, 1.8 * inch], small=True),
    p("Management decision now required", "H1X"),
    p("This task reports completeness; it does not decide downstream treatment. Management must decide whether 300 deterministic identities and 199 fully covered prior-two histories are sufficient before authorizing any Y2/Y3 materialization."),
    p("Persisted reproducibility package", "H2X"),
    table([
        ["Artifact", "Purpose"],
        ["replacement_identity_materialization_coordinate.json", "Row-complete 335-player crosswalk and PIT inputs"],
        ["provider_identity_snapshot.json", "Exact governed identity fields and provider provenance"],
        ["manifest.json", "Input/output hashes, frozen rules, independence declaration"],
        ["collision_unmatched_audit.json", "All 35 unmatched rows and uniqueness audits"],
        ["sentinel_identity_audit.json", "Eight-sentinel identity/history status"],
        ["pit_coverage_audit.json", "Coverage counts and frozen-method parity"],
        ["reload_verification.json", "Fresh-read 335-row and hash verification"],
        ["RECONSTRUCTION.md", "Exact input hashes, command, and expected results"],
    ], [3.7 * inch, 3.15 * inch], small=True),
    p("STOP. Do not materialize the 335-player Y2/Y3 Forecast board, run sentinel Forecast parity, run Intrinsic/Shapley, tune, refit, implement, promote, merge, or deploy under this authority.", "StopX"),
]

doc = SimpleDocTemplate(str(OUT), pagesize=letter, rightMargin=0.7 * inch, leftMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.75 * inch, title="FSFFL NEXT Replacement Identity Materialization Coordinate", author="OpenAI Codex")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
