"""Step 3.5: Visual-consistency QA subagent.

After the illustrator renders each panel, this subagent:

1. Rasterizes the panel's SVG into a PNG (Gemini-generated pages embed the
   raw PNG, which is extracted directly; authored SVGs go through svglib).
2. Sends that PNG plus a structured "scene brief" to the configured vision
   model — Claude OR Gemini, whichever text provider the run selected.
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
import base64
import textwrap
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from concurrent.futures import ThreadPoolExecutor

from pydantic import ValidationError

from .config import SETTINGS
from .models import Panel, PanelQAReport, Scene, Storyboard
from .prompts import QA_REVIEWER_SYSTEM


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

# Marker for "the REVIEW itself errored" (placeholder score 50). These reports
# describe a broken reviewer call, not a bad page — so they must trigger a
# review retry, never an image regeneration.
REVIEW_ERROR_PREFIX = "QA reviewer call failed"


def is_review_error(report: PanelQAReport) -> bool:
    return any(i.startswith(REVIEW_ERROR_PREFIX) for i in report.issues)


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
    client:
        Shared vision-capable text client (Anthropic ``ClaudeClient`` or
        ``GeminiTextClient`` — both expose ``complete_json_with_image``).
    model:
        Optional model override for the vision calls.
    """

    def __init__(
        self,
        client,
        *,
        model: str | None = None,
    ) -> None:
        self._claude = client
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
                # Generous budget: thinking models (Gemini 3.x) spend output
                # tokens on reasoning before the JSON appears.
                max_tokens=3000,
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
                issues=[f"{REVIEW_ERROR_PREFIX}: {type(exc).__name__}: {exc}"],
                suggestions=[],
            )

        report.retry_count = retry_count
        return report

    # ----- Batch entry point ---------------------------------------------- #

    def review_all(
        self,
        storyboard: Storyboard,
        panels: list[Panel],
        *,
        max_workers: int = 4,
    ) -> list[PanelReview]:
        """Review every panel and return paired verdicts (in scene order).

        Reviews run CONCURRENTLY (they are independent vision calls), unlike
        page rendering which must stay sequential for visual consistency.
        """

        panels_by_num = {p.scene_number: p for p in panels}
        jobs = [
            (scene, panels_by_num[scene.number])
            for scene in storyboard.scenes
            if scene.number in panels_by_num
        ]

        def _one(job) -> PanelReview:
            scene, panel = job
            report = self.review(
                scene=scene,
                panel=panel,
                art_style=storyboard.art_style,
                cast=storyboard.cast,
            )
            return PanelReview(scene=scene, panel=panel, report=report)

        if len(jobs) <= 1:
            return [_one(j) for j in jobs]
        with ThreadPoolExecutor(max_workers=min(max_workers, len(jobs))) as ex:
            return list(ex.map(_one, jobs))


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
    root = ET.fromstring(svg_markup)

    embedded = _embedded_image_as_png_from_svg(root)
    if embedded is not None:
        return embedded

    # Prefer cairosvg when installed — it renders authored SVGs much more
    # faithfully than svglib/renderPM.
    try:
        import cairosvg  # type: ignore

        return cairosvg.svg2png(bytestring=svg_markup.encode("utf-8"))
    except Exception:
        pass

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


def _embedded_image_as_png_from_svg(root: ET.Element) -> bytes | None:
    """Return embedded data-URI image bytes from a Gemini SVG wrapper as PNG."""

    for el in root.iter():
        for value in el.attrib.values():
            image_bytes = _decode_image_data_uri(value)
            if image_bytes is not None:
                return _image_bytes_to_png(image_bytes)
    return None


def _decode_image_data_uri(value: str) -> bytes | None:
    """Decode a base64 image data URI value if present."""

    marker = ";base64,"
    if not value.startswith("data:image/") or marker not in value:
        return None
    return base64.b64decode(value.split(marker, 1)[1])


def _image_bytes_to_png(image_bytes: bytes) -> bytes:
    """Normalize arbitrary image bytes to real PNG bytes for Claude vision."""

    from PIL import Image as PILImage

    with PILImage.open(io.BytesIO(image_bytes)) as pil:
        has_alpha = pil.mode in {"RGBA", "LA"} or (
            pil.mode == "P" and "transparency" in pil.info
        )
        image = pil.convert("RGBA" if has_alpha else "RGB")
        out = io.BytesIO()
        image.save(out, format="PNG")
        return out.getvalue()


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


def needs_regeneration(
    report: PanelQAReport, threshold: int | None = None
) -> bool:
    """True when a page should be re-rendered: hard "fail" verdict OR a
    consistency score below the threshold (default 80, configurable via
    ``C2C_QA_SCORE_THRESHOLD``).

    Review-error reports (placeholder score 50) are excluded — those mean the
    REVIEW broke, not the page; callers should retry the review instead of
    burning image credits."""

    if is_review_error(report):
        return False
    thr = SETTINGS.qa_score_threshold if threshold is None else threshold
    return report.verdict == "fail" or report.consistency_score < thr


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
