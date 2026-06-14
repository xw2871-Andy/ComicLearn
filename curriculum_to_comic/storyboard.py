"""Step 2: Turn a :class:`Lesson` into a 6-scene :class:`Storyboard`."""

from __future__ import annotations

import json

from .models import Lesson, Storyboard
from .prompts import STORYBOARD_SYSTEM, load_tuning


def build_storyboard(
    lesson: Lesson,
    claude,
    *,
    cast: list[str] | None = None,
    setting_hint: str | None = None,
) -> Storyboard:
    user_msg = _format_user_prompt(lesson, cast=cast, setting_hint=setting_hint)
    data = claude.complete_json(
        system=STORYBOARD_SYSTEM + load_tuning("storyboard"),
        user=user_msg,
        max_tokens=12000,
        temperature=0.7,
    )
    data.setdefault("lesson_title", lesson.title)
    data.setdefault("cast", cast or ["Doraemon", "Nobita"])
    storyboard = Storyboard.model_validate(data)

    # Defensive normalization: ensure exactly 6 scenes, numbered 1..N.
    storyboard.scenes = storyboard.scenes[:6]
    for i, scene in enumerate(storyboard.scenes, start=1):
        scene.number = i
    return storyboard


def _format_user_prompt(
    lesson: Lesson,
    *,
    cast: list[str] | None,
    setting_hint: str | None,
) -> str:
    cast_line = (
        f"Cast: {', '.join(cast)}"
        if cast
        else "Cast: Doraemon (mentor) and Nobita (curious student)"
    )
    setting_line = f"Setting hint: {setting_hint}" if setting_hint else ""

    lesson_json = json.dumps(lesson.model_dump(), indent=2, ensure_ascii=False)
    return (
        "# Storyboard request\n\n"
        f"{cast_line}\n"
        f"{setting_line}\n\n"
        "Convert the following lesson plan into a 6-scene comic storyboard "
        "following the system rules.\n\n"
        "## Lesson plan (JSON)\n\n"
        f"{lesson_json}\n\n"
        "Remember: output ONLY the storyboard JSON, no fences, no prose."
    )
