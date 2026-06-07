"""Normalize the three accepted input shapes into a :class:`CurriculumInput`.

Supported inputs:
- ``topic``: a short string + grade level (no file).
- ``markdown``: path to a ``.md`` / ``.txt`` file.
- ``pdf``: path to a textbook PDF. We extract text with pdfplumber and optionally
  ask Claude to narrow it down to the topic the user cares about.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from .claude_client import ClaudeClient
from .models import CurriculumInput
from .prompts import PDF_EXTRACT_SYSTEM


def from_topic(topic: str, grade_level: str) -> CurriculumInput:
    return CurriculumInput(
        title=topic.strip(),
        grade_level=grade_level.strip(),
        source_text=(
            f"Topic: {topic}\n"
            f"Grade level / course: {grade_level}\n"
            "No external source material was provided. Use canonical curricular "
            "knowledge for this topic and grade level."
        ),
        source_kind="topic",
    )


def from_markdown(path: Path, topic: str | None, grade_level: str) -> CurriculumInput:
    text = path.read_text(encoding="utf-8")
    title = topic.strip() if topic else _infer_title(text, fallback=path.stem)
    return CurriculumInput(
        title=title,
        grade_level=grade_level.strip(),
        source_text=text,
        source_kind="markdown",
    )


def from_pdf(
    path: Path,
    topic: str,
    grade_level: str,
    *,
    page_range: tuple[int, int] | None = None,
    claude: ClaudeClient | None = None,
    max_chars: int = 18_000,
) -> CurriculumInput:
    """Extract text from a textbook PDF.

    If a topic is given and the raw extract is long, we ask Claude to focus on
    the topic-relevant pages.
    """

    raw = _extract_pdf_text(path, page_range=page_range)
    relevant = raw
    if len(raw) > max_chars and topic and claude is not None:
        relevant = claude.complete(
            system=PDF_EXTRACT_SYSTEM,
            user=(
                f"Topic of interest: {topic}\n"
                f"Grade level: {grade_level}\n\n"
                f"Raw PDF text follows. Return a clean markdown extract focused "
                f"on this topic.\n\n---\n{raw[:max_chars * 2]}\n---"
            ),
            max_tokens=4096,
            temperature=0.2,
        )

    return CurriculumInput(
        title=topic.strip(),
        grade_level=grade_level.strip(),
        source_text=relevant,
        source_kind="pdf",
    )


def _extract_pdf_text(
    path: Path, page_range: tuple[int, int] | None = None
) -> str:
    """Pure-python PDF text extraction via pdfplumber."""

    chunks: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        pages = pdf.pages
        if page_range:
            lo, hi = page_range
            pages = pages[max(0, lo - 1) : hi]
        for i, page in enumerate(pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(f"--- Page {i} ---\n{text}")
    return "\n\n".join(chunks)


def _infer_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line and not line.startswith("---"):
            return line[:80]
    return fallback
