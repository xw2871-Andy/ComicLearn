"""High-level orchestrator that ties the pipeline steps together.

Pipeline (one Claude/Gemini call per step):

    1. Lesson plan       (Claude JSON)
    2. Storyboard        (Claude JSON, 6 scenes)
    3. Panel rendering   (SVG via Claude OR PNG via Gemini Nano Banana 2)
    3.5 Visual QA loop   (Claude vision reviews each panel; failed panels are
                         re-rendered with the reviewer's suggestions appended)
    4. PDF compile       (ReportLab + svglib)
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from .claude_client import ClaudeClient
from .compiler import compile_pdf
from .config import SETTINGS
from .illustrator import render_storyboard
from .lesson import build_lesson
from .models import ComicBook, CurriculumInput, Lesson, Panel, PanelQAReport, Storyboard
from .qa import PanelReview, StoryboardQAAgent, format_qa_suggestion_hint
from .storyboard import build_storyboard

console = Console()


@dataclass
class AgentResult:
    lesson: Lesson
    storyboard: Storyboard
    panels: list[Panel]
    book: ComicBook
    qa_reports: list[PanelQAReport] = field(default_factory=list)


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
        claude: ClaudeClient | None = None,
        output_dir: Path | None = None,
        *,
        cast: list[str] | None = None,
        setting_hint: str | None = None,
        reference_paths: list[Path] | None = None,
        chain_panels: bool = True,
        run_qa: bool = True,
        qa_retries: int = 1,
    ) -> None:
        self.claude = claude or ClaudeClient()
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

        step_count = 5 if self.run_qa else 4

        console.print(f"[cyan]Step 1/{step_count}[/cyan] Extracting lesson plan with Claude...")
        lesson = build_lesson(curriculum, self.claude)
        (run_dir / "lesson.json").write_text(
            lesson.model_dump_json(indent=2), encoding="utf-8"
        )
        console.print(f"  -> [green]{len(lesson.sections)} sections[/green] "
                      f"({lesson.unit_label})")

        console.print(f"[cyan]Step 2/{step_count}[/cyan] Writing 6-scene storyboard...")
        storyboard = build_storyboard(
            lesson,
            self.claude,
            cast=self.cast,
            setting_hint=self.setting_hint,
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
            f"[cyan]Step 3/{step_count}[/cyan] Rendering panels via "
            f"[bold]{backend_label}[/bold] backend{ref_label}..."
        )
        panels_dir = run_dir / "panels"
        panels_dir.mkdir(exist_ok=True)
        panels, backend = render_storyboard(
            storyboard,
            self.claude,
            reference_paths=self.reference_paths,
            chain_panels=self.chain_panels,
        )
        self._write_panels(panels, panels_dir)
        console.print(f"  -> [green]{len(panels)} panels[/green] saved to "
                      f"{panels_dir}")

        # ----- Step 3.5: visual-consistency QA subagent ----- #
        qa_reports: list[PanelQAReport] = []
        if self.run_qa:
            console.print(
                f"[cyan]Step 4/{step_count}[/cyan] QA reviewer judging each panel "
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

        final_step = step_count
        console.print(f"[cyan]Step {final_step}/{step_count}[/cyan] Compiling final PDF comic book...")
        pdf_path = run_dir / f"{_slug(lesson.title)}_comic.pdf"
        compile_pdf(
            pdf_path=pdf_path,
            lesson=lesson,
            storyboard=storyboard,
            panels=panels,
            qa_reports=qa_reports,
        )
        console.print(f"  -> [bold green]PDF ready:[/bold green] {pdf_path}")

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
            failing = [r for r in reviews_by_num.values() if r.report.verdict == "fail"]
            if not failing:
                break
            console.print(
                f"  [yellow]Retry pass {attempt}/{self.qa_retries}[/yellow]: "
                f"re-rendering {len(failing)} failing panel(s)..."
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
