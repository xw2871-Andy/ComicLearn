"""Step 1: Turn a normalized :class:`CurriculumInput` into a structured :class:`Lesson`."""

from __future__ import annotations

from .claude_client import ClaudeClient
from .models import CurriculumInput, Lesson
from .prompts import LESSON_PLANNER_SYSTEM


def build_lesson(curriculum: CurriculumInput, claude: ClaudeClient) -> Lesson:
    user_msg = _format_user_prompt(curriculum)
    data = claude.complete_json(
        system=LESSON_PLANNER_SYSTEM,
        user=user_msg,
        max_tokens=3500,
        temperature=0.4,
    )
    # Backfill the grade level if the model omits it.
    data.setdefault("grade_level", curriculum.grade_level)
    data.setdefault("title", curriculum.title)
    return Lesson.model_validate(data)


def _format_user_prompt(curriculum: CurriculumInput) -> str:
    return (
        f"# Lesson request\n\n"
        f"- Title: {curriculum.title}\n"
        f"- Grade level / course: {curriculum.grade_level}\n"
        f"- Source type: {curriculum.source_kind}\n\n"
        f"## Source material\n\n"
        f"{curriculum.source_text}\n\n"
        f"---\n\n"
        f"Produce the lesson plan JSON described in the system prompt. "
        f"Aim for 4-6 sections. Be mathematically/conceptually rigorous; if the "
        f"source text is thin (e.g. topic-only mode), draw on canonical "
        f"curricular knowledge for this grade level."
    )
