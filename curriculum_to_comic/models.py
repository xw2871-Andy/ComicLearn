"""Pydantic data models that flow through the pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CurriculumInput(BaseModel):
    """Normalized input to the agent."""

    title: str = Field(..., description="Short title for the lesson, e.g. 'Riemann Sums'.")
    grade_level: str = Field(
        ..., description="e.g. 'AP Calculus AB', 'Grade 7 Math', '9th-grade Biology'."
    )
    source_text: str = Field(
        ...,
        description="Raw curriculum content (topic description, markdown, or extracted PDF text).",
    )
    source_kind: Literal["topic", "markdown", "pdf"] = "topic"


class LessonSection(BaseModel):
    heading: str
    body: str = Field(..., description="Plain text / LaTeX explanation of the section.")
    key_terms: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class Lesson(BaseModel):
    """A structured lesson plan extracted from the source curriculum."""

    title: str
    grade_level: str
    unit_label: str = Field(
        ..., description="Curricular label, e.g. 'AP Calc AB Unit 6.2' or 'NGSS MS-LS1-5'."
    )
    essential_questions: list[str]
    learning_objectives: list[str]
    sections: list[LessonSection]
    misconceptions: list[str] = Field(default_factory=list)


class Dialogue(BaseModel):
    speaker: str
    text: str


class Scene(BaseModel):
    """One comic page / scene."""

    number: int
    title: str
    pedagogical_beat: str = Field(
        ...,
        description="One of: hook, context, definition, theorem, worked_example, "
        "misconception, recap.",
    )
    visual_description: str = Field(
        ..., description="What's happening visually in the panel."
    )
    holographic_math: str | None = Field(
        default=None, description="Math / formula overlay to show on the panel (LaTeX-ish)."
    )
    dialogue: list[Dialogue]
    caption: str | None = None


class Storyboard(BaseModel):
    lesson_title: str
    cast: list[str] = Field(
        ..., description="Recurring characters, e.g. ['Doraemon', 'Nobita']."
    )
    art_style: str = Field(
        default=(
            "Clean anime manga comic style, vibrant colors, educational illustration, "
            "bright glowing holographic math overlays."
        )
    )
    scenes: list[Scene]


class Panel(BaseModel):
    """A rendered comic panel ready for layout."""

    scene_number: int
    svg: str = Field(..., description="Full SVG markup for the panel.")
    caption: str | None = None
    dialogue: list[Dialogue]


class PanelQAReport(BaseModel):
    """Structured verdict from the visual-consistency QA subagent."""

    scene_number: int
    verdict: Literal["pass", "warn", "fail"]
    consistency_score: int = Field(
        ..., ge=0, le=100, description="Overall 0-100 visual quality score."
    )
    style_match: bool = Field(
        ..., description="True if the art style matches the storyboard's style spec."
    )
    visual_density: Literal["low", "medium", "high"] = Field(
        ...,
        description="low = single static shot; medium = 2 panels; high = 3+ manga-style panels.",
    )
    characters_present: bool
    dialogue_bubbles_readable: bool
    math_overlay_ok: bool = Field(
        default=True,
        description="True if the holographic math overlay (when required) is visible and legible.",
    )
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(
        default_factory=list,
        description="Concrete prompt-rewrite hints to address the issues on a retry.",
    )
    retry_count: int = Field(default=0, description="How many times this panel was regenerated.")


class ComicBook(BaseModel):
    """Final assembled artifact metadata."""

    title: str
    subtitle: str
    pdf_path: str
    storyboard_path: str
    dialogue_path: str
    panels_dir: str
    run_dir: str
