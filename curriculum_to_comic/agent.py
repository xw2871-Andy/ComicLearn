"""High-level orchestrator that ties the pipeline steps together.

Pipeline (text steps run on Claude OR Gemini, selected per run):

    1. Lesson plan       (text model, JSON)
    1.5 Worksheet        (text model, student-facing Markdown)
    2. Storyboard        (text model, JSON, 6 scenes)
    3. Page rendering    (Nano Banana Pro PNG, one page at a time,
                         OR SVG via the text model)
    3.5 Visual QA loop   (vision reviewer judges each page; failed pages are
                         re-rendered with the reviewer's suggestions appended)
    4. PDF compile       (ReportLab + svglib)
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from .compiler import compile_pdf
from .config import SETTINGS
from .illustrator import render_storyboard
from .lesson import build_lesson
from .llm import get_text_client
from .models import ComicBook, CurriculumInput, Lesson, Panel, PanelQAReport, Storyboard
from .qa import (
    PanelReview,
    StoryboardQAAgent,
    format_qa_suggestion_hint,
    needs_regeneration,
)
from .story_qa import review_and_fix
from .storyboard import build_storyboard
from .worksheet import build_worksheet

console = Console()


@dataclass
class AgentResult:
    lesson: Lesson
    storyboard: Storyboard
    panels: list[Panel]
    book: ComicBook
    qa_reports: list[PanelQAReport] = field(default_factory=list)
    worksheet_path: str | None = None


class ComicAgent:
    """The end-to-end agent.

    Typical usage::

        from curriculum_to_comic import ComicAgent
        from curriculum_to_comic.extractors import from_topic

        agent = ComicAgent()
        result = agent.run(from_topic("Riemann Sums", "AP Calculus AB"))
        print(result.book.pdf_path)
    """

    def __init__(
        self,
        claude=None,
        output_dir: Path | None = None,
        *,
        provider: str | None = None,
        cast: list[str] | None = None,
        setting_hint: str | None = None,
        reference_paths: list[Path] | None = None,
        chain_panels: bool = True,
        run_qa: bool = True,
        qa_retries: int = 1,
        image_quality: str | None = None,
        run_story_qa: bool = True,
        compile_pdf_output: bool = True,
    ) -> None:
        # `claude` keeps backwards compatibility; any text client works.
        self.claude = claude or get_text_client(provider)
        self.provider = SETTINGS.resolve_text_provider(provider)
        self.image_quality = image_quality
        self.run_story_qa = run_story_qa
        self.compile_pdf_output = compile_pdf_output
        self.output_dir = Path(output_dir or SETTINGS.default_output_dir).expanduser()
        self.cast = cast
        self.setting_hint = setting_hint
        self.reference_paths = [Path(p) for p in (reference_paths or [])]
        self.chain_panels = chain_panels
        self.run_qa = run_qa
        self.qa_retries = max(0, int(qa_retries))

    # ----- Pipeline ------------------------------------------------------- #

    def run(self, curriculum: CurriculumInput) -> AgentResult:
        run_dir = self._make_run_dir(curriculum.title)
        console.rule(f"[bold cyan]curriculum-to-comic | {curriculum.title}")

        step_count = 6 if self.run_qa else 5
        provider_label = self.provider

        console.print(
            f"[cyan]Step 1/{step_count}[/cyan] Extracting lesson plan "
            f"({provider_label})..."
        )
        lesson = build_lesson(curriculum, self.claude)
        (run_dir / "lesson.json").write_text(
            lesson.model_dump_json(indent=2), encoding="utf-8"
        )
        console.print(f"  -> [green]{len(lesson.sections)} sections[/green] "
                      f"({lesson.unit_label})")

        console.print(
            f"[cyan]Step 2/{step_count}[/cyan] Writing student worksheet..."
        )
        worksheet_md = build_worksheet(lesson, self.claude)
        worksheet_path = run_dir / "worksheet.md"
        worksheet_path.write_text(worksheet_md, encoding="utf-8")
        console.print(f"  -> [green]worksheet.md[/green] saved")

        console.print(f"[cyan]Step 3/{step_count}[/cyan] Writing 6-scene storyboard...")
        storyboard = build_storyboard(
            lesson,
            self.claude,
            cast=self.cast,
            setting_hint=self.setting_hint,
        )
        if self.run_story_qa:
            console.print(
                "  [cyan]·[/cyan] Story editor reviewing narrative flow..."
            )
            storyboard, story_report = review_and_fix(
                lesson,
                storyboard,
                self.claude,
                cast=self.cast,
                setting_hint=self.setting_hint,
            )
            (run_dir / "story_qa.json").write_text(
                __import__("json").dumps(story_report.to_dict(), indent=2),
                encoding="utf-8",
            )
            label = "revised" if story_report.revised else "kept"
            console.print(
                f"  -> story flow score [bold]{story_report.final_flow_score}"
                f"[/bold] ({label})"
            )
        (run_dir / "storyboard.json").write_text(
            storyboard.model_dump_json(indent=2), encoding="utf-8"
        )
        self._write_dialogue_txt(storyboard, run_dir / "dialogue.txt")
        console.print(f"  -> [green]{len(storyboard.scenes)} scenes[/green] "
                      f"with cast {storyboard.cast}")

        backend_label = SETTINGS.image_backend
        ref_label = ""
        if self.reference_paths:
            ref_label = f" with {len(self.reference_paths)} reference image(s)"
        if self.chain_panels and backend_label != "svg":
            ref_label += " + rolling self-reference"
        console.print(
            f"[cyan]Step 4/{step_count}[/cyan] Rendering pages one by one via "
            f"[bold]{backend_label}[/bold] backend{ref_label}..."
        )
        panels_dir = run_dir / "panels"
        panels_dir.mkdir(exist_ok=True)
        panels, backend = render_storyboard(
            storyboard,
            self.claude,
            reference_paths=self.reference_paths,
            chain_panels=self.chain_panels,
            resolution=self.image_quality,
        )
        self._write_panels(panels, panels_dir)
        console.print(f"  -> [green]{len(panels)} panels[/green] saved to "
                      f"{panels_dir}")

        # ----- Step 3.5: visual-consistency QA subagent ----- #
        qa_reports: list[PanelQAReport] = []
        if self.run_qa:
            console.print(
                f"[cyan]Step 5/{step_count}[/cyan] QA reviewer judging each panel "
                f"(up to {self.qa_retries} retry/retries per failing panel)..."
            )
            qa = StoryboardQAAgent(self.claude)
            panels, qa_reports = self._qa_loop(
                qa=qa,
                backend=backend,
                storyboard=storyboard,
                panels=panels,
                panels_dir=panels_dir,
            )
            (run_dir / "qa_reports.json").write_text(
                _dump_reports_json(qa_reports), encoding="utf-8"
            )
            self._print_qa_summary(qa_reports)

            # Book-level consistency review: all pages judged side by side
            # for character drift, garbled text, and visual storytelling.
            from .book_qa import best_page_png, pages_to_regenerate, review_book

            console.print("  [cyan]·[/cyan] Book reviewer judging all pages side by side...")
            book_rep = review_book(storyboard, panels, self.claude)
            if book_rep.error:
                console.print(f"  [yellow]book review skipped: {book_rep.error}[/yellow]")
            else:
                console.print(
                    f"  -> book consistency [bold]{book_rep.consistency_score}[/bold] "
                    f"· best page {book_rep.best_page}"
                )
                flagged = pages_to_regenerate(book_rep)
                if flagged:
                    console.print(
                        f"  [yellow]redrawing {len(flagged)} page(s) for "
                        f"cross-page consistency[/yellow]"
                    )
                    anchor = best_page_png(book_rep, panels)
                    panels_map = {p.scene_number: p for p in panels}
                    reports_map = {r.scene_number: r for r in qa_reports}
                    scenes_map = {s.number: s for s in storyboard.scenes}
                    for pr in flagged:
                        num = int(pr.get("page", 0) or 0)
                        scene = scenes_map.get(num)
                        if scene is None:
                            continue
                        hints = (
                            "BOOK CONSISTENCY FIXES (must apply): "
                            + (pr.get("regen_hints")
                               or "; ".join(pr.get("issues", [])[:4]))
                        )
                        if anchor is not None and hasattr(backend, "_last_panel_png"):
                            backend._last_panel_png = anchor
                        try:
                            new_panel = backend.render(
                                scene, storyboard.art_style, storyboard.cast,
                                extra_hints=hints,
                            )
                        except Exception as exc:  # pragma: no cover
                            console.print(f"    [red]page {num} redraw failed: {exc}[/red]")
                            continue
                        new_report = qa.review(
                            scene=scene, panel=new_panel,
                            art_style=storyboard.art_style,
                            cast=storyboard.cast, retry_count=2,
                        )
                        new_report.retry_count = 2
                        # KEEP-BETTER guard: discard a redraw that regresses.
                        old_score = reports_map[num].consistency_score
                        if new_report.consistency_score < old_score:
                            console.print(
                                f"    -> page {num} redraw scored "
                                f"{new_report.consistency_score} < {old_score}; "
                                f"keeping original"
                            )
                            continue
                        panels_map[num] = new_panel
                        reports_map[num] = new_report
                        book_rep.regenerated_pages.append(num)
                        console.print(
                            f"    -> page {num} redrawn: "
                            f"[{_color(new_report.verdict)}]{new_report.verdict}[/] "
                            f"score={new_report.consistency_score}"
                        )
                    panels = [panels_map[s.number] for s in storyboard.scenes
                              if s.number in panels_map]
                    qa_reports = [reports_map[s.number] for s in storyboard.scenes
                                  if s.number in reports_map]
                    self._write_panels(panels, panels_dir)
                    (run_dir / "qa_reports.json").write_text(
                        _dump_reports_json(qa_reports), encoding="utf-8"
                    )
            import json as _json_mod

            (run_dir / "book_qa.json").write_text(
                _json_mod.dumps(book_rep.to_dict(), indent=2), encoding="utf-8"
            )

        final_step = step_count
        pdf_path = run_dir / f"{_slug(lesson.title)}_comic.pdf"
        if self.compile_pdf_output:
            console.print(f"[cyan]Step {final_step}/{step_count}[/cyan] Compiling final PDF comic book...")
            compile_pdf(
                pdf_path=pdf_path,
                lesson=lesson,
                storyboard=storyboard,
                panels=panels,
                qa_reports=qa_reports,
            )
            console.print(f"  -> [bold green]PDF ready:[/bold green] {pdf_path}")
        else:
            console.print("  -> [dim]PDF compile skipped (components-only mode)[/dim]")

        book = ComicBook(
            title=lesson.title,
            subtitle=f"{lesson.unit_label} - {lesson.grade_level}",
            pdf_path=str(pdf_path),
            storyboard_path=str(run_dir / "storyboard.json"),
            dialogue_path=str(run_dir / "dialogue.txt"),
            panels_dir=str(panels_dir),
            run_dir=str(run_dir),
        )
        (run_dir / "book.json").write_text(
            book.model_dump_json(indent=2), encoding="utf-8"
        )
        console.rule("[bold green]Done")
        return AgentResult(
            lesson=lesson,
            storyboard=storyboard,
            panels=panels,
            book=book,
            qa_reports=qa_reports,
            worksheet_path=str(worksheet_path),
        )

    # ----- QA helpers ----------------------------------------------------- #

    def _qa_loop(
        self,
        *,
        qa: StoryboardQAAgent,
        backend,
        storyboard: Storyboard,
        panels: list[Panel],
        panels_dir: Path,
    ) -> tuple[list[Panel], list[PanelQAReport]]:
        """Review every panel; re-render failing ones up to ``qa_retries`` times."""

        reviews: list[PanelReview] = qa.review_all(storyboard, panels)
        # First pass dump.
        for r in reviews:
            console.print(
                f"  - Scene {r.scene.number}: "
                f"[{_color(r.report.verdict)}]{r.report.verdict}[/]"
                f" score={r.report.consistency_score} "
                f"density={r.report.visual_density}"
            )

        scenes_by_num = {s.number: s for s in storyboard.scenes}
        reviews_by_num = {r.scene.number: r for r in reviews}

        for attempt in range(1, self.qa_retries + 1):
            failing = [
                r for r in reviews_by_num.values()
                if needs_regeneration(r.report)
            ]
            if not failing:
                break
            console.print(
                f"  [yellow]Retry pass {attempt}/{self.qa_retries}[/yellow]: "
                f"re-rendering {len(failing)} panel(s) "
                f"(verdict=fail or score<{SETTINGS.qa_score_threshold})..."
            )
            for r in failing:
                scene = scenes_by_num[r.scene.number]
                hints = format_qa_suggestion_hint(r.report)
                try:
                    new_panel = backend.render(
                        scene,
                        storyboard.art_style,
                        storyboard.cast,
                        extra_hints=hints,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    console.print(
                        f"    [red]Retry render failed for scene "
                        f"{scene.number}: {exc}[/red]"
                    )
                    continue

                new_report = qa.review(
                    scene=scene,
                    panel=new_panel,
                    art_style=storyboard.art_style,
                    cast=storyboard.cast,
                    retry_count=attempt,
                )
                # Belt-and-suspenders: ensure retry_count reflects this pass
                # even if the reviewer subagent forgot to honor the kwarg.
                new_report.retry_count = attempt
                # KEEP-BETTER guard: a redraw that scores lower than the page
                # it replaces is discarded, so quality only ratchets upward.
                old_score = reviews_by_num[scene.number].report.consistency_score
                if new_report.consistency_score < old_score:
                    console.print(
                        f"    -> scene {scene.number} redraw scored "
                        f"{new_report.consistency_score} < {old_score}; "
                        f"keeping original"
                    )
                    continue
                reviews_by_num[scene.number] = PanelReview(
                    scene=scene, panel=new_panel, report=new_report
                )
                console.print(
                    f"    -> scene {scene.number} re-reviewed: "
                    f"[{_color(new_report.verdict)}]{new_report.verdict}[/] "
                    f"score={new_report.consistency_score}"
                )

        # Materialize final panel + report lists in scene order.
        final_panels: list[Panel] = []
        final_reports: list[PanelQAReport] = []
        for scene in storyboard.scenes:
            r = reviews_by_num.get(scene.number)
            if r is None:
                continue
            final_panels.append(r.panel)
            final_reports.append(r.report)

        # Persist any updated panel SVGs.
        self._write_panels(final_panels, panels_dir)
        return final_panels, final_reports

    @staticmethod
    def _print_qa_summary(reports: list[PanelQAReport]) -> None:
        if not reports:
            return
        passed = sum(1 for r in reports if r.verdict == "pass")
        warned = sum(1 for r in reports if r.verdict == "warn")
        failed = sum(1 for r in reports if r.verdict == "fail")
        avg = sum(r.consistency_score for r in reports) / len(reports)
        console.print(
            f"  -> QA summary: [green]{passed} pass[/green], "
            f"[yellow]{warned} warn[/yellow], "
            f"[red]{failed} fail[/red], "
            f"avg consistency score [bold]{avg:.1f}[/bold]"
        )

    # ----- Misc helpers --------------------------------------------------- #

    @staticmethod
    def _write_panels(panels: list[Panel], panels_dir: Path) -> None:
        for p in panels:
            (panels_dir / f"scene_{p.scene_number:02d}.svg").write_text(
                p.svg, encoding="utf-8"
            )

    def _make_run_dir(self, title: str) -> Path:
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = self.output_dir / "runs" / f"{ts}_{_slug(title)}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    @staticmethod
    def _write_dialogue_txt(storyboard: Storyboard, path: Path) -> None:
        lines: list[str] = []
        for scene in storyboard.scenes:
            lines.append(f"# Scene {scene.number}: {scene.title}")
            for d in scene.dialogue:
                lines.append(f"{d.speaker}: {d.text}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")


def _dump_reports_json(reports: list[PanelQAReport]) -> str:
    import json

    return json.dumps([r.model_dump() for r in reports], indent=2)


def _color(verdict: str) -> str:
    return {"pass": "green", "warn": "yellow", "fail": "red"}.get(verdict, "white")


def _slug(text: str) -> str:
    return (
        "".join(c if c.isalnum() else "_" for c in text.lower())
        .strip("_")
        .replace("__", "_")
    )[:60] or "lesson"
