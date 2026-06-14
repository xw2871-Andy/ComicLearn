"""Normalize the three accepted input shapes into a :class:`CurriculumInput`.

Supported inputs:
- ``topic``: a short string + grade level (no file).
- ``markdown``: path to a ``.md`` / ``.txt`` file.
- ``pdf``: path to a textbook PDF. Text is extracted with Mathpix OCR when
  ``MATHPIX_APP_ID``/``MATHPIX_APP_KEY`` are configured (best for math —
  preserves LaTeX), falling back to local pdfplumber extraction otherwise.
  Long extracts are optionally narrowed to the requested topic by the text
  model (Claude or Gemini).
"""

from __future__ import annotations

from pathlib import Path

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
    claude=None,
    client=None,
    max_chars: int = 18_000,
    on_status=None,
) -> CurriculumInput:
    """Extract text from a textbook PDF.

    Mathpix OCR is used when configured (LaTeX-accurate math), else
    pdfplumber. If a topic is given and the raw extract is long, we ask the
    text model to focus on the topic-relevant pages.

    ``client`` (or legacy alias ``claude``) may be any text client from
    :func:`curriculum_to_comic.llm.get_text_client`. ``on_status`` is an
    optional ``callable(str)`` used to surface progress messages.
    """

    llm = client or claude
    notify = on_status or (lambda _msg: None)

    raw = _extract_pdf_text(path, page_range=page_range, notify=notify)
    if not raw.strip():
        raise RuntimeError(
            "No text could be extracted from this PDF. If it is a scanned "
            "document, configure MATHPIX_APP_ID / MATHPIX_APP_KEY for OCR."
        )

    relevant = raw
    if len(raw) > max_chars and topic and llm is not None:
        notify("Narrowing the extract to the requested topic…")
        relevant = llm.complete(
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
    path: Path,
    page_range: tuple[int, int] | None = None,
    notify=lambda _msg: None,
) -> str:
    """Extract PDF text: Mathpix OCR when configured, else pdfplumber."""

    from . import mathpix

    if mathpix.mathpix_available():
        try:
            notify("Extracting PDF with Mathpix OCR (LaTeX-accurate math)…")
            return mathpix.extract_pdf_markdown(path, page_range=page_range)
        except mathpix.MathpixError as exc:
            notify(f"Mathpix failed ({exc}); falling back to local extraction.")

    notify("Extracting PDF text locally with pdfplumber…")
    return _pdfplumber_text(path, page_range=page_range)


def _pdfplumber_text(
    path: Path, page_range: tuple[int, int] | None = None
) -> str:
    """Pure-python PDF text extraction via pdfplumber."""

    import pdfplumber

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
