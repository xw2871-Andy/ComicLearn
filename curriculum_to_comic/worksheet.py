"""Step 1.5: Turn a :class:`Lesson` into a printable student worksheet.

Ports the OpenClaw `lesson_plan` skill's worksheet output
(`outputs/worksheets/[lesson_name]_worksheet.md`) into the pipeline: the
structured lesson JSON is rewritten as a polished, student-facing Markdown
worksheet that the teacher can download alongside the comic.
"""

from __future__ import annotations

import json

from .models import Lesson
from .prompts import WORKSHEET_SYSTEM


def build_worksheet(lesson: Lesson, client) -> str:
    """Return the worksheet as a Markdown string."""

    lesson_json = json.dumps(lesson.model_dump(), indent=2, ensure_ascii=False)
    raw = client.complete(
        system=WORKSHEET_SYSTEM,
        user=(
            "# Worksheet request\n\n"
            "Convert the following structured lesson plan into the worksheet "
            "format described in your system instructions.\n\n"
            "## Lesson plan (JSON)\n\n"
            f"{lesson_json}\n\n"
            "Output ONLY the Markdown worksheet."
        ),
        max_tokens=10000,
        temperature=0.4,
    )
    return _strip_outer_fence(raw)


def _strip_outer_fence(text: str) -> str:
    """Remove a single wrapping ```...``` fence if the model added one."""

    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1 and t.endswith("```"):
            return t[first_nl + 1 : -3].strip()
    return t
