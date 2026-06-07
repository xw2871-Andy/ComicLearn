"""Step 4: Compile rendered panels + storyboard into a polished comic-book PDF.

Layout per scene = one PDF page:
    +---------------------------------------------+
    | Header bar: "Scene N: title" + beat tag      |
    +---------------------------------------------+
    |                                             |
    |          SVG panel art (~70% of page)        |
    |                                             |
    +---------------------------------------------+
    | Dialogue block (speaker -> line)             |
    | Caption (italic, narrator-style)             |
    +---------------------------------------------+

The cover page summarizes the lesson (title, grade, essential questions,
objectives) and a closing page lists misconceptions / "what to watch for".
"""

from __future__ import annotations

import io
from pathlib import Path
from xml.etree import ElementTree as ET

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

from .models import Lesson, Panel, PanelQAReport, Storyboard

# ----- Page geometry ------------------------------------------------------- #

PAGE_W, PAGE_H = LETTER
MARGIN = 0.5 * inch
PANEL_HEIGHT = 6.2 * inch  # leaves room for dialogue + header

# ----- Stylesheet ---------------------------------------------------------- #


def _stylesheet() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "TitleBig": ParagraphStyle(
            "TitleBig",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=colors.HexColor("#111827"),
            alignment=1,
            spaceAfter=8,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=14,
            textColor=colors.HexColor("#4b5563"),
            alignment=1,
            spaceAfter=20,
        ),
        "SectionH": ParagraphStyle(
            "SectionH",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#111827"),
        ),
        "Caption": ParagraphStyle(
            "Caption",
            parent=base["Italic"],
            fontName="Helvetica-Oblique",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#374151"),
            backColor=colors.HexColor("#fef9c3"),
            borderColor=colors.HexColor("#facc15"),
            borderWidth=1,
            borderPadding=6,
            spaceBefore=8,
        ),
        "Speaker": ParagraphStyle(
            "Speaker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.HexColor("#1d4ed8"),
        ),
        "SceneHeader": ParagraphStyle(
            "SceneHeader",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=colors.white,
            backColor=colors.HexColor("#1f2937"),
            borderPadding=8,
            spaceAfter=10,
        ),
    }


# ----- SVG -> drawing helper ---------------------------------------------- #


def _svg_to_image_flowable(svg_markup: str, max_w: float, max_h: float) -> Image | Paragraph:
    """Convert an SVG string into a ReportLab Image flowable via svglib + PNG."""

    try:
        # Sanity-check that the SVG is well-formed XML.
        ET.fromstring(svg_markup)
        drawing = svg2rlg(io.StringIO(svg_markup))
        if drawing is None:
            raise ValueError("svglib returned None")

        # Rasterize via reportlab's renderPM to PNG bytes for embedding.
        from reportlab.graphics import renderPM

        # Scale the drawing into the available box while preserving aspect.
        scale = min(max_w / drawing.width, max_h / drawing.height)
        drawing.width *= scale
        drawing.height *= scale
        drawing.scale(scale, scale)

        png_bytes = renderPM.drawToString(drawing, fmt="PNG", dpi=180)
        return Image(io.BytesIO(png_bytes), width=drawing.width, height=drawing.height)
    except Exception as exc:  # pragma: no cover - defensive
        return Paragraph(
            f"<i>[Panel could not be rasterized: {type(exc).__name__}: {exc}]</i>",
            _stylesheet()["Caption"],
        )


# ----- Public entry point -------------------------------------------------- #


def compile_pdf(
    *,
    pdf_path: Path,
    lesson: Lesson,
    storyboard: Storyboard,
    panels: list[Panel],
    qa_reports: list[PanelQAReport] | None = None,
) -> Path:
    styles = _stylesheet()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=lesson.title,
        author="curriculum-to-comic",
    )

    story: list = []

    # ---- Cover page ---- #
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph(lesson.title, styles["TitleBig"]))
    story.append(
        Paragraph(
            f"{lesson.unit_label} &middot; {lesson.grade_level}", styles["Subtitle"]
        )
    )
    story.append(Paragraph("Essential questions", styles["SectionH"]))
    for q in lesson.essential_questions:
        story.append(Paragraph(f"\u2022 {q}", styles["Body"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Learning objectives", styles["SectionH"]))
    for o in lesson.learning_objectives:
        story.append(Paragraph(f"\u2022 {o}", styles["Body"]))
    story.append(PageBreak())

    # ---- One PDF page per scene ---- #
    panels_by_num = {p.scene_number: p for p in panels}
    for scene in storyboard.scenes:
        panel = panels_by_num.get(scene.number)
        story.append(
            Paragraph(
                f"Scene {scene.number}: {scene.title}  &nbsp; "
                f"<font size='10'>[{scene.pedagogical_beat}]</font>",
                styles["SceneHeader"],
            )
        )
        if panel:
            avail_w = PAGE_W - 2 * MARGIN
            img = _svg_to_image_flowable(panel.svg, avail_w, PANEL_HEIGHT)
            story.append(img)
            story.append(Spacer(1, 0.15 * inch))

        # Dialogue table.
        rows = []
        for d in scene.dialogue:
            rows.append(
                [
                    Paragraph(f"<b>{d.speaker}</b>", styles["Speaker"]),
                    Paragraph(d.text, styles["Body"]),
                ]
            )
        if rows:
            table = Table(rows, colWidths=[1.2 * inch, PAGE_W - 2 * MARGIN - 1.2 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        (
                            "ROWBACKGROUNDS",
                            (0, 0),
                            (-1, -1),
                            [colors.HexColor("#f3f4f6"), colors.white],
                        ),
                    ]
                )
            )
            story.append(table)

        if scene.caption:
            story.append(Paragraph(scene.caption, styles["Caption"]))

        story.append(PageBreak())

    # ---- Misconceptions / debrief ---- #
    if lesson.misconceptions:
        story.append(Paragraph("Common student misconceptions", styles["TitleBig"]))
        story.append(Spacer(1, 0.2 * inch))
        for m in lesson.misconceptions:
            story.append(Paragraph(f"\u26a0 {m}", styles["Body"]))
            story.append(Spacer(1, 0.08 * inch))

    # ---- QA appendix (one row per scene) ---- #
    if qa_reports:
        story.append(PageBreak())
        story.append(Paragraph("Visual QA report", styles["TitleBig"]))
        story.append(
            Paragraph(
                "Per-panel verdict from the visual-consistency reviewer subagent.",
                styles["Subtitle"],
            )
        )

        header = [
            Paragraph("<b>Scene</b>", styles["Body"]),
            Paragraph("<b>Verdict</b>", styles["Body"]),
            Paragraph("<b>Score</b>", styles["Body"]),
            Paragraph("<b>Density</b>", styles["Body"]),
            Paragraph("<b>Notes</b>", styles["Body"]),
        ]
        verdict_colors = {
            "pass": colors.HexColor("#16a34a"),
            "warn": colors.HexColor("#ca8a04"),
            "fail": colors.HexColor("#dc2626"),
        }
        rows = [header]
        for r in qa_reports:
            color = verdict_colors.get(r.verdict, colors.HexColor("#111827"))
            notes_bits: list[str] = []
            if r.issues:
                notes_bits.append("Issues: " + "; ".join(r.issues[:2]))
            if r.suggestions:
                notes_bits.append("Tips: " + "; ".join(r.suggestions[:2]))
            if r.retry_count:
                notes_bits.append(f"(re-rendered {r.retry_count}x)")
            notes_text = " | ".join(notes_bits) or "OK"
            rows.append(
                [
                    Paragraph(str(r.scene_number), styles["Body"]),
                    Paragraph(
                        f'<font color="{color.hexval()}"><b>{r.verdict}</b></font>',
                        styles["Body"],
                    ),
                    Paragraph(str(r.consistency_score), styles["Body"]),
                    Paragraph(r.visual_density, styles["Body"]),
                    Paragraph(notes_text, styles["Body"]),
                ]
            )
        qa_table = Table(
            rows,
            colWidths=[
                0.6 * inch,
                0.9 * inch,
                0.7 * inch,
                0.9 * inch,
                PAGE_W - 2 * MARGIN - 3.1 * inch,
            ],
        )
        qa_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
                ]
            )
        )
        story.append(qa_table)

    doc.build(story)
    return pdf_path
