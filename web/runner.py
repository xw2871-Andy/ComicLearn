"""Background runner that drives the comic generation pipeline.

The runner is intentionally split from FastAPI: it does NOT depend on
``fastapi`` so it can also be invoked from the CLI or a notebook for
debugging.

It handles three things:

1. Imports the ``curriculum_to_comic`` pipeline lazily so the web layer
   still boots even if heavy deps (anthropic, svglib, reportlab, pdfplumber)
   aren't installed yet.
2. Wraps the existing pipeline functions one step at a time so we can emit
   progress events between them (DB-backed, also queued for live SSE).
3. Exposes a per-run pub/sub of events via :class:`RunBus` so the SSE
   endpoint can stream them to the browser.
"""

from __future__ import annotations

import os
import queue
import threading
import time
import traceback
from pathlib import Path
from typing import Any

from . import db

# ---- live event bus (in-memory) -------------------------------------------- #


class RunBus:
    """Per-run multi-subscriber event queue (memory-only, replay via DB)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, list[queue.Queue]] = {}
        self._done: set[str] = set()

    def publish(self, run_id: str, event: dict) -> None:
        with self._lock:
            qs = list(self._subs.get(run_id, []))
            if event.get("kind") in ("done", "error"):
                self._done.add(run_id)
        for q in qs:
            try:
                q.put_nowait(event)
            except queue.Full:  # pragma: no cover
                pass

    def subscribe(self, run_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=512)
        with self._lock:
            self._subs.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q: queue.Queue) -> None:
        with self._lock:
            subs = self._subs.get(run_id)
            if not subs:
                return
            try:
                subs.remove(q)
            except ValueError:
                pass
            if not subs and run_id in self._done:
                self._subs.pop(run_id, None)

    def is_done(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._done


BUS = RunBus()


# ---- emit helper ----------------------------------------------------------- #


class _Emitter:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._seq = 0
        self._lock = threading.Lock()

    def emit(self, kind: str, **payload: Any) -> None:
        with self._lock:
            self._seq += 1
            seq = self._seq
        event = {"kind": kind, "seq": seq, "payload": payload, "ts": int(time.time())}
        try:
            db.append_event(self.run_id, seq, kind, payload)
        except Exception:  # pragma: no cover
            traceback.print_exc()
        BUS.publish(self.run_id, event)


# ---- the actual pipeline runner ------------------------------------------- #


def start_run(
    *,
    run_id: str,
    title: str,
    grade_level: str,
    source_kind: str,
    source_text: str | None,
    backend: str,
    run_qa: bool,
    cast: list[str] | None,
    setting_hint: str | None,
    output_root: Path,
) -> threading.Thread:
    """Kick off the pipeline in a background thread. Returns the thread."""

    t = threading.Thread(
        target=_run_pipeline,
        name=f"c2c-run-{run_id[:8]}",
        kwargs=dict(
            run_id=run_id,
            title=title,
            grade_level=grade_level,
            source_kind=source_kind,
            source_text=source_text,
            backend=backend,
            run_qa=run_qa,
            cast=cast,
            setting_hint=setting_hint,
            output_root=output_root,
        ),
        daemon=True,
    )
    t.start()
    return t


def _run_pipeline(
    *,
    run_id: str,
    title: str,
    grade_level: str,
    source_kind: str,
    source_text: str | None,
    backend: str,
    run_qa: bool,
    cast: list[str] | None,
    setting_hint: str | None,
    output_root: Path,
) -> None:
    em = _Emitter(run_id)
    db.update_run(run_id, status="running")
    em.emit("info", message=f"Run started · backend={backend} · QA={run_qa}")

    # Force backend choice for this run.
    os.environ["IMAGE_BACKEND"] = backend

    try:
        # Lazy imports so the web app boots even without heavy deps installed.
        try:
            from curriculum_to_comic.agent import ComicAgent  # noqa: F401
            from curriculum_to_comic.claude_client import ClaudeClient
            from curriculum_to_comic.config import SETTINGS  # noqa: F401
            from curriculum_to_comic.extractors import from_markdown, from_topic
            from curriculum_to_comic.illustrator import render_storyboard
            from curriculum_to_comic.lesson import build_lesson
            from curriculum_to_comic.qa import (
                StoryboardQAAgent,
                format_qa_suggestion_hint,
            )
            from curriculum_to_comic.storyboard import build_storyboard
            from curriculum_to_comic.compiler import compile_pdf
            from curriculum_to_comic.models import (
                PanelQAReport,  # noqa: F401
            )
        except Exception as exc:  # pragma: no cover - dep load failure
            raise RuntimeError(
                "The curriculum_to_comic package failed to import "
                "(missing dependency?). Run `pip install -e .` first. "
                f"Underlying error: {exc}"
            ) from exc

        # 1) Build CurriculumInput from the inputs we have.
        em.emit("step", step=1, total=5, label="Loading curriculum input")
        if source_kind == "topic":
            curriculum = from_topic(title, grade_level)
        elif source_kind == "markdown":
            md_path = output_root / "runs" / "_inputs" / f"{run_id}.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(source_text or "", encoding="utf-8")
            curriculum = from_markdown(md_path, title, grade_level)
        else:
            raise RuntimeError(
                f"source_kind={source_kind!r} not supported by the web runner "
                "(PDF upload is a follow-up; use markdown for now)."
            )

        # Per-run output directory under the project's outputs/runs/.
        run_dir = output_root / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        panels_dir = run_dir / "panels"
        panels_dir.mkdir(exist_ok=True)
        db.update_run(run_id, run_dir=str(run_dir))

        claude = ClaudeClient()

        # 2) Lesson plan.
        em.emit("step", step=2, total=5, label="Drafting lesson plan with Claude")
        lesson = build_lesson(curriculum, claude)
        (run_dir / "lesson.json").write_text(
            lesson.model_dump_json(indent=2), encoding="utf-8"
        )
        em.emit(
            "info",
            message=f"Lesson ready: {lesson.unit_label} · {len(lesson.sections)} sections",
        )

        # 3) Storyboard.
        em.emit("step", step=3, total=5, label="Writing 6-scene storyboard")
        storyboard = build_storyboard(
            lesson, claude, cast=cast, setting_hint=setting_hint
        )
        (run_dir / "storyboard.json").write_text(
            storyboard.model_dump_json(indent=2), encoding="utf-8"
        )
        em.emit(
            "info",
            message=f"Storyboard ready · {len(storyboard.scenes)} scenes "
                    f"· cast {storyboard.cast}",
        )

        # 4) Panel rendering.
        em.emit(
            "step",
            step=4,
            total=5,
            label=f"Rendering panels via {backend} backend",
        )
        panels, backend_obj = render_storyboard(
            storyboard, claude, reference_paths=[], chain_panels=True
        )
        for p in panels:
            svg_path = panels_dir / f"scene_{p.scene_number:02d}.svg"
            svg_path.write_text(p.svg, encoding="utf-8")
            em.emit(
                "panel",
                scene=p.scene_number,
                caption=p.caption,
                path=str(svg_path.relative_to(output_root)),
            )

        # 4.5) QA loop.
        qa_reports = []
        if run_qa:
            em.emit("step", step=5, total=5, label="Visual QA subagent reviewing")
            qa = StoryboardQAAgent(claude)
            reviews = qa.review_all(storyboard, panels)
            reviews_by_num = {r.scene.number: r for r in reviews}
            for r in reviews:
                em.emit(
                    "info",
                    message=f"  scene {r.scene.number}: {r.report.verdict} "
                            f"(score={r.report.consistency_score})",
                )

            # one retry pass on failing panels
            failing = [r for r in reviews_by_num.values() if r.report.verdict == "fail"]
            if failing:
                em.emit(
                    "warn",
                    message=f"Retrying {len(failing)} failing panel(s)",
                )
                scenes_by_num = {s.number: s for s in storyboard.scenes}
                for r in failing:
                    scene = scenes_by_num[r.scene.number]
                    hints = format_qa_suggestion_hint(r.report)
                    try:
                        new_panel = backend_obj.render(
                            scene,
                            storyboard.art_style,
                            storyboard.cast,
                            extra_hints=hints,
                        )
                    except Exception as exc:
                        em.emit(
                            "warn",
                            message=f"  scene {scene.number}: retry failed ({exc})",
                        )
                        continue
                    new_report = qa.review(
                        scene=scene,
                        panel=new_panel,
                        art_style=storyboard.art_style,
                        cast=storyboard.cast,
                        retry_count=1,
                    )
                    new_report.retry_count = 1
                    from curriculum_to_comic.qa import PanelReview  # local import

                    reviews_by_num[scene.number] = PanelReview(
                        scene=scene, panel=new_panel, report=new_report
                    )
                    (panels_dir / f"scene_{scene.number:02d}.svg").write_text(
                        new_panel.svg, encoding="utf-8"
                    )

            # finalize panel + report list in scene order
            final_panels = []
            qa_reports = []
            for scene in storyboard.scenes:
                rr = reviews_by_num.get(scene.number)
                if not rr:
                    continue
                final_panels.append(rr.panel)
                qa_reports.append(rr.report)
            panels = final_panels

            import json as _json

            (run_dir / "qa_reports.json").write_text(
                _json.dumps([r.model_dump() for r in qa_reports], indent=2),
                encoding="utf-8",
            )

        # 5) Compile PDF.
        em.emit("step", step=5, total=5, label="Compiling PDF comic book")
        pdf_path = run_dir / f"{_slug(lesson.title)}_comic.pdf"
        compile_pdf(
            pdf_path=pdf_path,
            lesson=lesson,
            storyboard=storyboard,
            panels=panels,
            qa_reports=qa_reports,
        )

        db.update_run(
            run_id,
            status="done",
            pdf_path=str(pdf_path),
            finished_at=db.now_ts(),
        )
        em.emit(
            "done",
            pdf_path=str(pdf_path.relative_to(output_root)),
            run_dir=str(run_dir.relative_to(output_root)),
            message="PDF ready",
        )

    except Exception as exc:  # pragma: no cover
        tb = traceback.format_exc()
        db.update_run(
            run_id, status="error", error=str(exc), finished_at=db.now_ts()
        )
        em.emit("error", message=str(exc), traceback=tb)


# ---- mock runner (always available, for UI dev / sandbox demo) ------------ #


def start_mock_run(*, run_id: str, title: str, output_root: Path) -> threading.Thread:
    """A self-contained fake run that streams realistic events + recycles the
    existing Unit 1.1 showcase pages as the gallery output. Lets the studio
    UI be demoed even when the real agent's API deps aren't reachable."""

    t = threading.Thread(
        target=_run_mock,
        name=f"c2c-mock-{run_id[:8]}",
        kwargs=dict(run_id=run_id, title=title, output_root=output_root),
        daemon=True,
    )
    t.start()
    return t


def _run_mock(*, run_id: str, title: str, output_root: Path) -> None:
    em = _Emitter(run_id)
    db.update_run(run_id, status="running")
    run_dir = output_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db.update_run(run_id, run_dir=str(run_dir))

    em.emit("info", message=f"[mock] Generating comic for: {title}")
    em.emit("step", step=1, total=5, label="Loading curriculum input")
    time.sleep(0.5)
    em.emit("step", step=2, total=5, label="Drafting lesson plan with Claude")
    time.sleep(0.7)
    em.emit("step", step=3, total=5, label="Writing 6-scene storyboard")
    time.sleep(0.7)
    em.emit("step", step=4, total=5, label="Rendering panels (SVG backend)")

    # Recycle the showcase pages so the gallery has something to display.
    showcase = (
        output_root.parent / "samples" / "showcase" / "Unit_1.1_Limits_Pages"
    )
    captions = [
        "Curiosity · The Cookie Conundrum",
        "Definition · A limit is where things are going",
        "Visualization · Walking toward x = 3",
        "Theorem · The graph with a hole",
        "Failure · Jump discontinuity, limit DNE",
        "Synthesis · Tale of three points",
    ]
    panels_dir = run_dir / "panels"
    panels_dir.mkdir(exist_ok=True)
    for i in range(1, 7):
        src = showcase / f"page{i}.png"
        if src.exists():
            dst = panels_dir / f"scene_{i:02d}.png"
            dst.write_bytes(src.read_bytes())
            em.emit(
                "panel",
                scene=i,
                caption=captions[i - 1],
                path=str(dst.relative_to(output_root)),
            )
        time.sleep(0.4)

    em.emit("step", step=5, total=5, label="QA + PDF compile")
    time.sleep(0.6)
    em.emit("info", message="[mock] All 6 panels passed QA (avg score 92)")
    em.emit(
        "done",
        pdf_path="",
        run_dir=str(run_dir.relative_to(output_root)),
        message="Mock run complete · gallery populated from Unit 1.1 showcase",
    )
    db.update_run(run_id, status="done", finished_at=db.now_ts())


def _slug(text: str) -> str:
    return (
        "".join(c if c.isalnum() else "_" for c in (text or "").lower())
        .strip("_")
        .replace("__", "_")
    )[:60] or "lesson"
