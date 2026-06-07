"""Step 3.5: Visual-consistency QA subagent.

After the illustrator renders each panel, this subagent:

1. Rasterizes the panel's SVG into a PNG using svglib + reportlab.renderPM
   (the same path the PDF compiler uses, so we judge what the reader will see).
2. Sends that PNG plus a structured "scene brief" to Claude vision.
3. Receives a strict-JSON :class:`PanelQAReport` verdict on six axes:
   style match, visual density, scene fidelity, dialogue bubble readability,
   math overlay visibility, and series consistency.

The orchestrator (see :mod:`curriculum_to_comic.agent`) then uses these reports
to decide whether to re-render any panel with the QA-suggested prompt hints
appended to the original brief, capped by ``max_retries``.

This mirrors the original DoraeMath ``check-image-condition`` skill that lived
in the OpenClaw workspace, ported into the new typed Python pipeline.
"""

from __future__ import annotations

import io
import textwrap
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from pydantic import ValidationError

from .claude_client import ClaudeClient
from .models import Panel, PanelQAReport, Scene, Storyboard
from .prompts import QA_REVIEWER_SYSTEM


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


@dataclass
class PanelReview:
    """Bundles a panel with its QA verdict for downstream consumers."""

    scene: Scene
    panel: Panel
    report: PanelQAReport


class StoryboardQAAgent:
    """Vision-based reviewer that judges one panel at a time.

    Parameters
    ----------
    claude:
        Shared :class:`ClaudeClient` (vision-capable).
    model:
        Optional override for the Claude model used in vision calls. Defaults
        to whatever ``SETTINGS.reasoning_model`` is in the env.
    """

    def __init__(
        self,
        claude: ClaudeClient,
        *,
        model: str | None = None,
    ) -> None:
        self._claude = claude
        self._model = model

    # ----- One panel at a time --------------------------------------------- #

    def review(
        self,
        *,
        scene: Scene,
        panel: Panel,
        art_style: str,
        cast: list[str],
        retry_count: int = 0,
    ) -> PanelQAReport:
        """Score a single panel against its storyboard brief."""

        png_bytes = _rasterize_svg_to_png(panel.svg)
        brief = _format_qa_brief(scene, art_style=art_style, cast=cast)

        try:
            raw = self._claude.complete_json_with_image(
                system=QA_REVIEWER_SYSTEM,
                user_text=brief,
                image_bytes=png_bytes,
                model=self._model,
                max_tokens=1024,
                temperature=0.1,
            )
            # The reviewer is supposed to echo scene_number, but if it
            # forgets, we patch it in to keep the report aligned.
            raw.setdefault("scene_number", scene.number)
            report = PanelQAReport.model_validate(raw)
        except (ValidationError, ValueError, RuntimeError) as exc:
            # On any reviewer failure we WARN rather than blocking the
            # pipeline — the user still gets their PDF and a visible note in
            # the appendix that QA didn't run cleanly on this panel.
            report = PanelQAReport(
                scene_number=scene.number,
                verdict="warn",
                consistency_score=50,
                style_match=True,
                visual_density="medium",
                characters_present=True,
                dialogue_bubbles_readable=True,
                math_overlay_ok=True,
                issues=[f"QA reviewer call failed: {type(exc).__name__}: {exc}"],
                suggestions=[],
            )

        report.retry_count = retry_count
        return report

    # ----- Batch entry point ---------------------------------------------- #

    def review_all(
        self,
        storyboard: Storyboard,
        panels: list[Panel],
    ) -> list[PanelReview]:
        """Review every panel in a storyboard and return paired verdicts."""

        panels_by_num = {p.scene_number: p for p in panels}
        results: list[PanelReview] = []
        for scene in storyboard.scenes:
            panel = panels_by_num.get(scene.number)
            if panel is None:
                continue
            report = self.review(
                scene=scene,
                panel=panel,
                art_style=storyboard.art_style,
                cast=storyboard.cast,
            )
            results.append(PanelReview(scene=scene, panel=panel, report=report))
        return results


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _format_qa_brief(scene: Scene, *, art_style: str, cast: list[str]) -> str:
    """Compose the reviewer's text prompt explaining what the panel SHOULD show."""

    dialogue_lines = (
        "\n".join(f"  - {d.speaker}: {d.text}" for d in scene.dialogue)
        or "  - (no dialogue)"
    )
    math_line = scene.holographic_math or "(none required)"
    return textwrap.dedent(
        f"""
        # Panel QA brief

        You are reviewing the attached rendered comic panel against the
        storyboard scene that produced it.

        Scene #{scene.number}: "{scene.title}"
        Pedagogical beat: {scene.pedagogical_beat}
        Expected cast on screen: {', '.join(cast)}
        Expected art style: {art_style}

        Visual description the illustrator was given:
        {scene.visual_description}

        Required holographic math overlay: {math_line}

        Required dialogue (each line ideally appears in a short speech bubble):
        {dialogue_lines}

        Required caption (narrator box, optional): {scene.caption or "(none)"}

        Now grade the panel on the six axes from your system instructions and
        return the JSON verdict.
        """
    ).strip()


def _rasterize_svg_to_png(svg_markup: str, *, dpi: int = 144) -> bytes:
    """Rasterize an SVG string to PNG bytes for the vision reviewer.

    The pipeline is intentionally the same one the PDF compiler uses
    (``svglib.svg2rlg`` + ``reportlab.graphics.renderPM``) so the reviewer
    judges what the reader will actually see in the printed PDF, not a
    different renderer's output.
    """

    # Cheap well-formed-XML check so we surface broken SVGs early.
    ET.fromstring(svg_markup)

    # Imported lazily so unit tests that never touch this code path don't
    # incur the heavy reportlab/svglib import cost.
    from reportlab.graphics import renderPM
    from svglib.svglib import svg2rlg

    drawing = svg2rlg(io.StringIO(svg_markup))
    if drawing is None:
        raise ValueError("svglib could not parse the panel SVG.")
    try:
        return renderPM.drawToString(drawing, fmt="PNG", dpi=dpi)
    except Exception:
        # Some lightweight Python installs lack ReportLab's optional
        # renderPM/rlPyCairo backend. Keep QA non-blocking by sending a simple
        # PNG payload rather than failing before the reviewer can respond.
        return _fallback_svg_preview_png(svg_markup)


def _fallback_svg_preview_png(svg_markup: str) -> bytes:
    """Create a minimal PNG preview when SVG rasterization is unavailable."""

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (800, 1000), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 776, 976), outline=(30, 30, 30), width=4)
    draw.text((48, 52), "ComicTeach SVG preview", fill=(30, 30, 30))
    draw.text(
        (48, 92),
        "ReportLab raster backend unavailable; using QA fallback image.",
        fill=(90, 90, 90),
    )
    snippet = " ".join(svg_markup.split())[:520]
    y = 150
    for line in textwrap.wrap(snippet, width=72)[:12]:
        draw.text((48, y), line, fill=(80, 80, 80))
        y += 26

    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def format_qa_suggestion_hint(report: PanelQAReport) -> str:
    """Build a regen prompt hint string from a failed QA report.

    Used by the orchestrator's retry loop to bolt the reviewer's concrete
    suggestions onto the original illustrator brief without reinventing it.
    """

    parts: list[str] = []
    if report.issues:
        parts.append("Issues to fix: " + "; ".join(report.issues[:4]))
    if report.suggestions:
        parts.append("Apply: " + "; ".join(report.suggestions[:4]))
    if report.visual_density == "low":
        parts.append(
            "Split the page into 3+ sub-panels with thick black manga gutters."
        )
    if not report.dialogue_bubbles_readable:
        parts.append(
            "Render dialogue inside white speech bubbles with thick black "
            "strokes and tails pointing at the speaker."
        )
    if not report.style_match:
        parts.append(
            "Honor the storyboard's art style spec exactly; no photorealism."
        )
    if not report.math_overlay_ok:
        parts.append(
            "Add the required math overlay as a glowing cyan/magenta hologram."
        )
    return " ".join(parts).strip()
