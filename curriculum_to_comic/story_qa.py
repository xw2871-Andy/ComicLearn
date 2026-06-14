"""Step 2.5: Story-flow QA subagent.

Before any page is drawn, a "manga story editor" reviews the storyboard for
narrative smoothness: a grounded hook (no abrupt intros), pre-knowledge
activated before new theory, scene-to-scene bridges, proper theory
development (motivation -> intuition -> statement -> worked use), character
logic, and a resolution that recaps. Storyboards scoring below the threshold
are rewritten once with the editor's notes and re-reviewed.

This runs on TEXT only — it is cheap and fast compared to image generation,
and catching a broken story here saves six expensive page renders.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .models import Lesson, Storyboard
from .prompts import STORY_REVIEWER_SYSTEM, STORYBOARD_SYSTEM, load_tuning


def story_score_threshold() -> int:
    return int(os.getenv("C2C_STORY_SCORE_THRESHOLD", "75"))


@dataclass
class StoryQAReport:
    verdict: str = "pass"
    flow_score: int = 0
    issues: list[str] = field(default_factory=list)
    revision_instructions: str = ""
    revised: bool = False
    final_flow_score: int = 0

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "flow_score": self.flow_score,
            "issues": self.issues,
            "revision_instructions": self.revision_instructions,
            "revised": self.revised,
            "final_flow_score": self.final_flow_score,
        }


def review_storyboard(lesson: Lesson, storyboard: Storyboard, client) -> dict:
    """One review pass. Returns the raw reviewer JSON (defensive defaults)."""

    user = (
        "# Story-flow review request\n\n"
        "## Lesson plan (JSON)\n"
        f"{json.dumps(lesson.model_dump(), ensure_ascii=False)}\n\n"
        "## Storyboard to review (JSON)\n"
        f"{storyboard.model_dump_json()}\n\n"
        "Review per your system instructions and return ONLY the JSON verdict."
    )
    raw = client.complete_json(
        system=STORY_REVIEWER_SYSTEM,
        user=user,
        max_tokens=2000,
        temperature=0.2,
    )
    raw.setdefault("verdict", "pass")
    raw.setdefault("flow_score", 80)
    raw.setdefault("issues", [])
    raw.setdefault("revision_instructions", "")
    return raw


def revise_storyboard(
    lesson: Lesson,
    storyboard: Storyboard,
    instructions: str,
    client,
    *,
    cast: list[str] | None = None,
    setting_hint: str | None = None,
) -> Storyboard:
    """Rewrite the storyboard applying the story editor's notes."""

    cast_line = f"Cast: {', '.join(cast)}" if cast else ""
    setting_line = f"Setting hint: {setting_hint}" if setting_hint else ""
    user = (
        "# Storyboard REVISION request\n\n"
        f"{cast_line}\n{setting_line}\n\n"
        "A story editor reviewed your previous storyboard and requires these "
        "changes (apply ALL of them while keeping everything that already "
        "worked):\n\n"
        f"{instructions}\n\n"
        "## Lesson plan (JSON)\n"
        f"{json.dumps(lesson.model_dump(), ensure_ascii=False)}\n\n"
        "## Previous storyboard (JSON)\n"
        f"{storyboard.model_dump_json()}\n\n"
        "Return ONLY the full revised storyboard JSON, same schema, no fences."
    )
    data = client.complete_json(
        system=STORYBOARD_SYSTEM + load_tuning("storyboard"),
        user=user,
        max_tokens=12000,
        temperature=0.6,
    )
    data.setdefault("lesson_title", lesson.title)
    data.setdefault("cast", cast or storyboard.cast)
    revised = Storyboard.model_validate(data)
    revised.scenes = revised.scenes[:6]
    for i, scene in enumerate(revised.scenes, start=1):
        scene.number = i
    return revised


def review_and_fix(
    lesson: Lesson,
    storyboard: Storyboard,
    client,
    *,
    cast: list[str] | None = None,
    setting_hint: str | None = None,
    threshold: int | None = None,
) -> tuple[Storyboard, StoryQAReport]:
    """Review the storyboard; rewrite once if it falls below the threshold.

    Returns (best_storyboard, report). Never raises on reviewer failure —
    a broken reviewer falls back to passing the original storyboard so the
    pipeline keeps moving.
    """

    thr = story_score_threshold() if threshold is None else threshold
    report = StoryQAReport()
    try:
        first = review_storyboard(lesson, storyboard, client)
    except Exception as exc:
        report.issues = [f"Story reviewer failed: {type(exc).__name__}: {exc}"]
        report.flow_score = report.final_flow_score = -1
        return storyboard, report

    report.verdict = str(first.get("verdict", "pass"))
    report.flow_score = int(first.get("flow_score", 80))
    report.issues = list(first.get("issues", []))[:8]
    report.revision_instructions = str(first.get("revision_instructions", ""))
    report.final_flow_score = report.flow_score

    needs_fix = report.verdict == "revise" or report.flow_score < thr
    if not needs_fix:
        return storyboard, report

    try:
        revised = revise_storyboard(
            lesson,
            storyboard,
            report.revision_instructions or "; ".join(report.issues),
            client,
            cast=cast,
            setting_hint=setting_hint,
        )
        second = review_storyboard(lesson, revised, client)
        report.revised = True
        report.final_flow_score = int(second.get("flow_score", report.flow_score))
        # Keep whichever version scored better.
        if report.final_flow_score >= report.flow_score:
            return revised, report
        report.final_flow_score = report.flow_score
        return storyboard, report
    except Exception as exc:
        report.issues.append(
            f"Storyboard revision failed ({type(exc).__name__}); using original."
        )
        return storyboard, report
