"""Step 3.75: Book-level consistency QA (the strongest reviewer).

Per-page QA judges each page in isolation, which can never catch DRIFT —
Doraemon subtly off-model on page 4, a palette shift on page 5, a setting
that quietly mutates. This reviewer sees ALL pages of the book side by side
in a single vision call and grades exactly the three things teachers worry
about most:

1. **Character consistency** — same faces, proportions, colors on every page.
2. **Accuracy** — bubble text legible and correctly spelled; math overlays
   match the storyboard's exact formulas; nothing garbled.
3. **Visual storytelling** — page N+1 visibly continues page N's action and
   setting; the book reads as one continuous story.

Pages flagged below the threshold are re-rendered with the reviewer's
concrete hints (and the book's BEST page attached as an extra style anchor),
then the per-page QA re-checks them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .models import Panel, Storyboard
from .qa import _rasterize_svg_to_png

BOOK_REVIEWER_SYSTEM = """You are the series supervisor for a published
Doraemon educational manga. You receive ALL pages of one comic book at once
(labeled Page 1..N) plus the storyboard. You are the last gate before print,
and you specialize in catching what page-by-page reviewers miss: drift,
inaccuracy, and broken visual storytelling ACROSS pages.

Grade the BOOK on three axes:

1. **Character & style consistency (most important).** Pick the page where
   the cast looks most on-model (classic Doraemon: blue robot cat, white
   face/belly, red collar, gold bell; Nobita: round glasses, yellow shirt).
   Then flag every page that deviates from it: proportions, face shape,
   colors, line weight, palette, rendering style. Be strict — a reader
   flipping pages must never feel the artist changed.

2. **Accuracy.** On every page: is ALL bubble text legible, correctly
   spelled English, and faithful to the storyboard dialogue? Are the math
   overlays EXACTLY the storyboard's formulas (no mangled notation, no
   invented symbols)? Flag any garbled text, wrong formula, or wrong values.

3. **Visual storytelling.** Does each page visually continue the previous
   one (same location unless the story moves them, consistent props,
   continuing action)? Does the book open in a grounded scene, escalate, and
   resolve? Flag abrupt visual jumps where a reader would feel a page is
   missing.

For every flagged page give CONCRETE regeneration hints phrased as image-
prompt additions (e.g. "Doraemon must have his red collar and gold bell,
rounder head, same blue as page 2" or "keep the bakery interior from page 3
with the same wooden counter").

`consistency_score` is for the BOOK as a whole, 0-100. Below 75 means at
least one page must be regenerated. Reserve 90+ for books with zero visible
drift and perfect text.

Return ONLY this JSON, no fences:

{
  "book_verdict": "pass" | "fix",
  "consistency_score": 0-100,
  "best_page": int,
  "summary": str,
  "page_reports": [
    {
      "page": int,
      "on_model": bool,
      "text_accurate": bool,
      "continues_story": bool,
      "issues": [str, ...],
      "regen_hints": str
    }, ...
  ]
}"""


def book_score_threshold() -> int:
    return int(os.getenv("C2C_BOOK_SCORE_THRESHOLD", "75"))


# Cap how many pages one book-QA pass may regenerate (cost control).
MAX_BOOK_REGENS = int(os.getenv("C2C_BOOK_MAX_REGENS", "2"))


@dataclass
class BookQAReport:
    book_verdict: str = "pass"
    consistency_score: int = 0
    best_page: int = 1
    summary: str = ""
    page_reports: list[dict] = field(default_factory=list)
    regenerated_pages: list[int] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "book_verdict": self.book_verdict,
            "consistency_score": self.consistency_score,
            "best_page": self.best_page,
            "summary": self.summary,
            "page_reports": self.page_reports,
            "regenerated_pages": self.regenerated_pages,
            "error": self.error,
        }


def _format_brief(storyboard: Storyboard) -> str:
    lines = [
        "# Book review brief",
        f"Art style spec: {storyboard.art_style}",
        f"Cast: {', '.join(storyboard.cast)}",
        "",
        "Storyboard (what each page must show and say):",
    ]
    for s in storyboard.scenes:
        dlg = " / ".join(f'{d.speaker}: "{d.text}"' for d in s.dialogue[:3])
        lines.append(
            f"- Page {s.number} [{s.pedagogical_beat}] {s.title}: "
            f"{s.visual_description[:220]} · math: "
            f"{s.holographic_math or '(none)'} · key dialogue: {dlg}"
        )
    lines.append(
        "\nNow grade the attached pages per your system instructions and "
        "return ONLY the JSON verdict."
    )
    return "\n".join(lines)


def review_book(storyboard: Storyboard, panels: list[Panel], client) -> BookQAReport:
    """One whole-book review pass. Never raises — degrades to a pass report
    with an `error` note so the pipeline keeps moving."""

    report = BookQAReport()
    try:
        ordered = sorted(panels, key=lambda p: p.scene_number)
        images = [_rasterize_svg_to_png(p.svg) for p in ordered]
        raw = client.complete_json_with_images(
            system=BOOK_REVIEWER_SYSTEM,
            user_text=_format_brief(storyboard),
            images=images,
            max_tokens=3000,
            temperature=0.1,
        )
        report.book_verdict = str(raw.get("book_verdict", "pass"))
        report.consistency_score = int(raw.get("consistency_score", 80))
        report.best_page = int(raw.get("best_page", 1) or 1)
        report.summary = str(raw.get("summary", ""))
        report.page_reports = list(raw.get("page_reports", []))
    except Exception as exc:
        report.error = f"Book reviewer failed: {type(exc).__name__}: {exc}"
    return report


def pages_to_regenerate(report: BookQAReport) -> list[dict]:
    """Worst-first list of page reports that need a redraw, capped."""

    if report.error:
        return []
    flagged = [
        pr for pr in report.page_reports
        if not pr.get("on_model", True)
        or not pr.get("text_accurate", True)
        or not pr.get("continues_story", True)
        or pr.get("issues")
    ]
    if report.book_verdict != "fix" and report.consistency_score >= book_score_threshold():
        return []
    flagged.sort(key=lambda pr: (
        pr.get("on_model", True),
        pr.get("text_accurate", True),
        -len(pr.get("issues", [])),
    ))
    return flagged[:MAX_BOOK_REGENS]


def best_page_png(report: BookQAReport, panels: list[Panel]) -> bytes | None:
    """PNG bytes of the reviewer's best page, used as an extra style anchor
    when regenerating flagged pages."""

    by_num = {p.scene_number: p for p in panels}
    panel = by_num.get(report.best_page)
    if panel is None:
        return None
    try:
        return _rasterize_svg_to_png(panel.svg)
    except Exception:
        return None
