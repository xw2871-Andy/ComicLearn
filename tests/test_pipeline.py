"""Offline tests that don't require an Anthropic API key.

These verify the non-LLM machinery: the input extractors, the JSON-lenient
parser, the SVG fallback, and the PDF compiler. The LLM-calling modules
(`lesson`, `storyboard`, `illustrator`) are exercised via dependency
injection of a stub ClaudeClient.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Provide a dummy key BEFORE importing the package so `Settings.from_env` is
# happy. None of these tests actually call Anthropic.
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-not-real")


def test_json_lenient_parser_handles_fenced_response() -> None:
    from curriculum_to_comic.claude_client import _parse_json_lenient

    response = "Sure! Here is the JSON you requested:\n```json\n{\"a\": 1, \"b\": [2, 3]}\n```\n"
    assert _parse_json_lenient(response) == {"a": 1, "b": [2, 3]}


def test_json_lenient_parser_handles_raw_object() -> None:
    from curriculum_to_comic.claude_client import _parse_json_lenient

    assert _parse_json_lenient('{"x": "y"}') == {"x": "y"}


def test_claude_client_retries_without_deprecated_temperature() -> None:
    from types import SimpleNamespace

    from curriculum_to_comic.claude_client import ClaudeClient

    calls: list[dict[str, object]] = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            if "temperature" in kwargs:
                raise RuntimeError("`temperature` is deprecated for this model.")
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="ok")],
                stop_reason="end_turn",
            )

    client = ClaudeClient.__new__(ClaudeClient)
    client._client = SimpleNamespace(messages=FakeMessages())

    assert client.complete(system="s", user="u", model="claude-test") == "ok"
    assert "temperature" in calls[0]
    assert "temperature" not in calls[1]


def test_version_metadata_matches_current_version() -> None:
    from curriculum_to_comic.version import get_release_history, get_version

    history = get_release_history()

    assert get_version() == history["current"]
    assert history["releases"]
    assert history["releases"][0]["version"] == get_version()
    assert history["releases"][0]["changes"]


def test_from_topic_normalizes_input() -> None:
    from curriculum_to_comic.extractors import from_topic

    inp = from_topic("Riemann Sums", "AP Calculus AB")
    assert inp.title == "Riemann Sums"
    assert inp.source_kind == "topic"
    assert "AP Calculus AB" in inp.source_text


def test_from_markdown_reads_file(tmp_path: Path) -> None:
    from curriculum_to_comic.extractors import from_markdown

    md = tmp_path / "lesson.md"
    md.write_text("# Photosynthesis\nIs the process by which plants...")

    inp = from_markdown(md, topic=None, grade_level="7th grade")
    assert inp.source_kind == "markdown"
    assert inp.title == "Photosynthesis"
    assert "Photosynthesis" in inp.source_text


def test_svg_fallback_is_valid_xml() -> None:
    from xml.etree import ElementTree as ET

    from curriculum_to_comic.illustrator import _fallback_svg
    from curriculum_to_comic.models import Dialogue, Scene

    scene = Scene(
        number=1,
        title="Test scene",
        pedagogical_beat="hook",
        visual_description="A test scene",
        dialogue=[Dialogue(speaker="Nobita", text="Hi!")],
    )
    svg = _fallback_svg(scene)
    # Must be parseable XML.
    ET.fromstring(svg)
    assert "Scene 1" in svg


def test_lesson_module_uses_claude_response() -> None:
    from curriculum_to_comic.extractors import from_topic
    from curriculum_to_comic.lesson import build_lesson

    fake = MagicMock()
    fake.complete_json.return_value = {
        "title": "Riemann Sums",
        "grade_level": "AP Calculus AB",
        "unit_label": "AP Calc AB Unit 6.2",
        "essential_questions": ["How do we approximate area?"],
        "learning_objectives": ["Write a Riemann sum."],
        "sections": [
            {
                "heading": "Context",
                "body": "Approximating area under a curve.",
                "key_terms": ["partition", "Delta x"],
                "examples": [],
            }
        ],
        "misconceptions": ["Forgetting Delta x."],
    }

    lesson = build_lesson(from_topic("Riemann Sums", "AP Calculus AB"), fake)
    assert lesson.title == "Riemann Sums"
    assert lesson.sections[0].heading == "Context"
    fake.complete_json.assert_called_once()


def test_storyboard_module_normalizes_scene_count() -> None:
    from curriculum_to_comic.models import Lesson
    from curriculum_to_comic.storyboard import build_storyboard

    fake = MagicMock()
    fake.complete_json.return_value = {
        "lesson_title": "Riemann Sums",
        "cast": ["Doraemon", "Nobita"],
        "art_style": "Anime",
        "scenes": [
            {
                "number": 99,  # will be normalized to 1..N
                "title": f"Scene {i}",
                "pedagogical_beat": "context",
                "visual_description": "Stuff happens",
                "holographic_math": None,
                "dialogue": [{"speaker": "Nobita", "text": "Whoa!"}],
                "caption": None,
            }
            for i in range(8)  # 8 returned, should clamp to 6
        ],
    }
    lesson = Lesson(
        title="Riemann Sums",
        grade_level="AP Calculus AB",
        unit_label="6.2",
        essential_questions=["Q?"],
        learning_objectives=["O"],
        sections=[],
    )

    sb = build_storyboard(lesson, fake)
    assert len(sb.scenes) == 6
    assert [s.number for s in sb.scenes] == [1, 2, 3, 4, 5, 6]


def test_gemini_backend_passes_static_and_rolling_references(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reference comic pages + previous panel must both be sent to Gemini."""

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    from curriculum_to_comic.image_backends.gemini_nano_banana import (
        GeminiNanoBananaBackend,
        MAX_REFS_PER_REQUEST,
    )
    from curriculum_to_comic.models import Dialogue, Scene

    static_ref = tmp_path / "style_sheet.png"
    static_ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"styleref" * 4)

    backend = GeminiNanoBananaBackend(
        api_key="test-gemini-key",
        reference_paths=[static_ref],
    )
    # Pretend a previous panel already rendered.
    backend._last_panel_png = b"PREVIOUS_PANEL_PNG"

    captured: dict[str, object] = {}

    def fake_call(self, prompt, references=None):
        captured["prompt"] = prompt
        captured["refs"] = references
        return b"NEW_PANEL_PNG"

    monkeypatch.setattr(GeminiNanoBananaBackend, "_call_gemini", fake_call)

    scene = Scene(
        number=2,
        title="Slope mystery",
        pedagogical_beat="context",
        visual_description="Nobita stares at a curve.",
        dialogue=[Dialogue(speaker="Nobita", text="What is that line?")],
    )
    panel = backend.render(scene, art_style="anime", cast=["Doraemon", "Nobita"])

    # Static ref + rolling ref were both sent, rolling one is last.
    refs = captured["refs"]
    assert len(refs) == 2
    assert refs[0][0].startswith(b"\x89PNG")  # static page
    assert refs[-1][0] == b"PREVIOUS_PANEL_PNG"  # rolling ref
    # Cap is honored if many static refs given.
    assert MAX_REFS_PER_REQUEST >= 2
    # Prompt explicitly demands consistency.
    assert "STRICT visual consistency" in captured["prompt"]
    # New panel was cached for the next call.
    assert backend._last_panel_png == b"NEW_PANEL_PNG"
    # PDF compiler will be fed an SVG wrapping the PNG.
    assert "data:image/png;base64," in panel.svg


def test_qa_subagent_parses_vision_verdict() -> None:
    """The QA subagent must turn Claude's vision JSON into a typed report."""

    from curriculum_to_comic.models import Dialogue, Panel, Scene, Storyboard
    from curriculum_to_comic.qa import StoryboardQAAgent

    scene = Scene(
        number=1,
        title="Hook",
        pedagogical_beat="hook",
        visual_description="Nobita sees a ramp.",
        dialogue=[Dialogue(speaker="Nobita", text="Why does it slope?")],
        holographic_math="$\\frac{dy}{dx}$",
    )
    panel = Panel(
        scene_number=1,
        # Tiny but valid SVG so the rasterizer doesn't throw.
        svg=(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000" '
            'width="800" height="1000">'
            '<rect width="800" height="1000" fill="#fff"/></svg>'
        ),
        caption=None,
        dialogue=[Dialogue(speaker="Nobita", text="Why does it slope?")],
    )

    fake = MagicMock()
    fake.complete_json_with_image.return_value = {
        "scene_number": 1,
        "verdict": "warn",
        "consistency_score": 72,
        "style_match": True,
        "visual_density": "medium",
        "characters_present": True,
        "dialogue_bubbles_readable": True,
        "math_overlay_ok": False,
        "issues": ["Math overlay not visible enough."],
        "suggestions": ["Add a glowing cyan dy/dx formula overlay."],
    }

    qa = StoryboardQAAgent(fake)
    report = qa.review(
        scene=scene,
        panel=panel,
        art_style="Anime manga",
        cast=["Doraemon", "Nobita"],
    )

    assert report.verdict == "warn"
    assert report.consistency_score == 72
    assert report.math_overlay_ok is False
    assert "glowing" in report.suggestions[0]
    fake.complete_json_with_image.assert_called_once()


def test_qa_suggestion_hint_assembles_actionable_directives() -> None:
    from curriculum_to_comic.models import PanelQAReport
    from curriculum_to_comic.qa import format_qa_suggestion_hint

    report = PanelQAReport(
        scene_number=2,
        verdict="fail",
        consistency_score=30,
        style_match=False,
        visual_density="low",
        characters_present=True,
        dialogue_bubbles_readable=False,
        math_overlay_ok=False,
        issues=["Photoreal style, single shot, no bubbles."],
        suggestions=["Use anime cel-shading.", "Render 3 sub-panels."],
    )
    hint = format_qa_suggestion_hint(report)
    assert "Issues to fix" in hint
    assert "Apply" in hint
    assert "sub-panels" in hint
    assert "speech bubbles" in hint
    assert "photorealism" in hint
    assert "math overlay" in hint


def test_agent_qa_retry_replaces_failing_panel() -> None:
    """A failed first verdict should trigger one re-render that the QA passes."""

    from curriculum_to_comic.agent import ComicAgent
    from curriculum_to_comic.models import (
        Dialogue,
        Lesson,
        Panel,
        PanelQAReport,
        Scene,
        Storyboard,
    )
    from curriculum_to_comic.qa import StoryboardQAAgent

    scene = Scene(
        number=1,
        title="Hook",
        pedagogical_beat="hook",
        visual_description="Nobita sees a ramp.",
        dialogue=[Dialogue(speaker="Nobita", text="Whoa.")],
    )
    storyboard = Storyboard(
        lesson_title="Slope",
        cast=["Doraemon", "Nobita"],
        scenes=[scene],
    )
    bad_panel = Panel(scene_number=1, svg="<svg/>", caption=None, dialogue=scene.dialogue)
    good_panel = Panel(
        scene_number=1, svg="<svg id='retry'/>", caption=None, dialogue=scene.dialogue
    )

    backend = MagicMock()
    backend.render.return_value = good_panel

    qa = MagicMock(spec=StoryboardQAAgent)
    # First batch review: fails.
    qa.review_all.return_value = [
        type(
            "PR",
            (),
            {
                "scene": scene,
                "panel": bad_panel,
                "report": PanelQAReport(
                    scene_number=1,
                    verdict="fail",
                    consistency_score=20,
                    style_match=False,
                    visual_density="low",
                    characters_present=False,
                    dialogue_bubbles_readable=False,
                    math_overlay_ok=True,
                    issues=["Wrong style."],
                    suggestions=["Anime manga, 3 sub-panels."],
                ),
            },
        )()
    ]
    # Re-review of the retry: passes.
    qa.review.return_value = PanelQAReport(
        scene_number=1,
        verdict="pass",
        consistency_score=92,
        style_match=True,
        visual_density="high",
        characters_present=True,
        dialogue_bubbles_readable=True,
        math_overlay_ok=True,
        issues=[],
        suggestions=[],
    )

    agent = ComicAgent.__new__(ComicAgent)
    agent.qa_retries = 2

    panels, reports = agent._qa_loop(
        qa=qa,
        backend=backend,
        storyboard=storyboard,
        panels=[bad_panel],
        panels_dir=Path("/tmp"),  # not actually written (mocked)
    )

    # The failing panel was replaced by the re-render and re-reviewed once.
    backend.render.assert_called_once()
    qa.review.assert_called_once()
    assert panels[0].svg == "<svg id='retry'/>"
    assert reports[0].verdict == "pass"
    assert reports[0].retry_count == 1


def test_pdf_compiles_with_fallback_panels(tmp_path: Path) -> None:
    from curriculum_to_comic.compiler import compile_pdf
    from curriculum_to_comic.illustrator import _fallback_svg
    from curriculum_to_comic.models import (
        Dialogue,
        Lesson,
        LessonSection,
        Panel,
        PanelQAReport,
        Scene,
        Storyboard,
    )

    lesson = Lesson(
        title="Demo Lesson",
        grade_level="AP Calculus AB",
        unit_label="Unit 6.2",
        essential_questions=["How do we approximate area under a curve?"],
        learning_objectives=["Build a right Riemann sum."],
        sections=[
            LessonSection(heading="Context", body="Area under a curve.", key_terms=[], examples=[])
        ],
        misconceptions=["Forgetting to multiply by Delta x."],
    )
    scenes = [
        Scene(
            number=i,
            title=f"Scene {i}",
            pedagogical_beat="context",
            visual_description="A test scene.",
            dialogue=[
                Dialogue(speaker="Doraemon", text="Look here, Nobita."),
                Dialogue(speaker="Nobita", text="Whoa, the rectangles fit!"),
            ],
            caption="The area is the limit of rectangles.",
        )
        for i in range(1, 4)
    ]
    storyboard = Storyboard(
        lesson_title=lesson.title,
        cast=["Doraemon", "Nobita"],
        scenes=scenes,
    )
    panels = [
        Panel(scene_number=s.number, svg=_fallback_svg(s), caption=s.caption, dialogue=s.dialogue)
        for s in scenes
    ]

    qa_reports = [
        PanelQAReport(
            scene_number=s.number,
            verdict="pass" if s.number != 2 else "warn",
            consistency_score=90 if s.number != 2 else 70,
            style_match=True,
            visual_density="high" if s.number != 2 else "medium",
            characters_present=True,
            dialogue_bubbles_readable=True,
            math_overlay_ok=True,
            issues=[] if s.number != 2 else ["Math overlay is faint."],
            suggestions=[] if s.number != 2 else ["Brighten the holographic glow."],
        )
        for s in scenes
    ]

    out_pdf = tmp_path / "demo.pdf"
    compile_pdf(
        pdf_path=out_pdf,
        lesson=lesson,
        storyboard=storyboard,
        panels=panels,
        qa_reports=qa_reports,
    )
    assert out_pdf.exists() and out_pdf.stat().st_size > 1000
