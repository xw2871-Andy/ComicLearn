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
from concurrent.futures import ThreadPoolExecutor
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
    def __init__(self, run_id: str, start_seq: int = 0) -> None:
        self.run_id = run_id
        self._seq = start_seq
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
    provider: str = "auto",
    source_path: str | None = None,
    page_range: tuple[int, int] | None = None,
    image_quality: str = "2K",
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
            provider=provider,
            source_path=source_path,
            page_range=page_range,
            image_quality=image_quality,
        ),
        daemon=True,
    )
    t.start()
    return t


TOTAL_STEPS = 8


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
    provider: str = "auto",
    source_path: str | None = None,
    page_range: tuple[int, int] | None = None,
    image_quality: str = "2K",
) -> None:
    em = _Emitter(run_id)
    db.update_run(run_id, status="running")

    # Force backend choice for this run.
    os.environ["IMAGE_BACKEND"] = backend

    try:
        # Lazy imports so the web app boots even without heavy deps installed.
        try:
            from curriculum_to_comic.config import SETTINGS
            from curriculum_to_comic.extractors import (
                from_markdown,
                from_pdf,
                from_topic,
            )
            from curriculum_to_comic.illustrator import render_storyboard
            from curriculum_to_comic.lesson import build_lesson
            from curriculum_to_comic.llm import get_text_client
            from curriculum_to_comic.qa import (
                StoryboardQAAgent,
                format_qa_suggestion_hint,
            )
            from curriculum_to_comic.storyboard import build_storyboard
            from curriculum_to_comic.worksheet import build_worksheet
            from curriculum_to_comic.compiler import compile_pdf
        except Exception as exc:  # pragma: no cover - dep load failure
            raise RuntimeError(
                "The curriculum_to_comic package failed to import "
                "(missing dependency?). Run `pip install -e .` first. "
                f"Underlying error: {exc}"
            ) from exc

        resolved_provider = SETTINGS.resolve_text_provider(provider)
        em.emit(
            "info",
            message=(
                f"Run started · text={resolved_provider} · images={backend} "
                f"· QA={'on' if run_qa else 'off'} "
                f"(regen below score {SETTINGS.qa_score_threshold})"
            ),
        )
        client = get_text_client(provider)

        # --- step timing ------------------------------------------------- #
        run_t0 = time.time()
        _cur = {"label": None, "t0": run_t0}

        def _step(n: int, label: str) -> None:
            now = time.time()
            if _cur["label"] is not None:
                em.emit(
                    "info",
                    message=f"⏱ {_cur['label']} took {now - _cur['t0']:.1f}s",
                )
            _cur["label"] = label
            _cur["t0"] = now
            em.emit("step", step=n, total=TOTAL_STEPS, label=label)

        # Per-run output directory under the project's outputs/runs/.
        run_dir = output_root / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        panels_dir = run_dir / "panels"
        panels_dir.mkdir(exist_ok=True)
        db.update_run(run_id, run_dir=str(run_dir))

        # 1) Build CurriculumInput from the inputs we have.
        _step(1, "Loading curriculum input")
        if source_kind == "topic":
            curriculum = from_topic(title, grade_level)
        elif source_kind == "markdown":
            md_path = output_root / "runs" / "_inputs" / f"{run_id}.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(source_text or "", encoding="utf-8")
            curriculum = from_markdown(md_path, title, grade_level)
        elif source_kind == "pdf":
            if not source_path or not Path(source_path).exists():
                raise RuntimeError("Uploaded PDF could not be found on disk.")
            curriculum = from_pdf(
                Path(source_path),
                topic=title,
                grade_level=grade_level,
                page_range=page_range,
                client=client,
                on_status=lambda msg: em.emit("info", message=msg),
            )
            em.emit(
                "info",
                message=(
                    f"PDF ingested · {len(curriculum.source_text)} chars of "
                    "curriculum text extracted"
                ),
            )
        else:
            raise RuntimeError(f"source_kind={source_kind!r} is not supported.")

        # 2) Lesson plan.
        _step(2, f"Drafting lesson plan ({resolved_provider})")
        lesson = build_lesson(curriculum, client)
        (run_dir / "lesson.json").write_text(
            lesson.model_dump_json(indent=2), encoding="utf-8"
        )
        em.emit(
            "info",
            message=f"Lesson ready: {lesson.unit_label} · {len(lesson.sections)} sections",
        )

        # 3) Worksheet — kicked off in the BACKGROUND so it overlaps with the
        # storyboard (both depend only on the lesson). Saves its full latency.
        _step(3, "Writing student worksheet (in background)")
        bg = ThreadPoolExecutor(max_workers=4, thread_name_prefix=f"c2c-bg-{run_id[:6]}")
        ws_future = bg.submit(build_worksheet, lesson, client)

        # 4) Storyboard (runs while the worksheet generates).
        _step(4, "Writing 6-scene storyboard")
        storyboard = build_storyboard(
            lesson, client, cast=cast, setting_hint=setting_hint
        )
        (run_dir / "storyboard.json").write_text(
            storyboard.model_dump_json(indent=2), encoding="utf-8"
        )
        em.emit(
            "info",
            message=f"Storyboard ready · {len(storyboard.scenes)} scenes "
                    f"· cast {storyboard.cast}",
        )

        # 5) Story-flow QA: a manga story editor reviews narrative smoothness
        # (grounded hook, pre-knowledge before theory, scene bridges, theory
        # development) and rewrites the storyboard once if it scores low.
        _step(5, "Story editor reviewing narrative flow")
        from curriculum_to_comic.story_qa import review_and_fix

        storyboard, story_report = review_and_fix(
            lesson, storyboard, client, cast=cast, setting_hint=setting_hint
        )
        (run_dir / "story_qa.json").write_text(
            __import__("json").dumps(story_report.to_dict(), indent=2),
            encoding="utf-8",
        )
        (run_dir / "storyboard.json").write_text(
            storyboard.model_dump_json(indent=2), encoding="utf-8"
        )
        if story_report.revised:
            em.emit(
                "info",
                message=(
                    f"Story flow: {story_report.flow_score} → storyboard "
                    f"revised → {story_report.final_flow_score}"
                ),
            )
        else:
            em.emit(
                "info",
                message=f"Story flow score: {story_report.final_flow_score} (kept)",
            )
        for issue in story_report.issues[:3]:
            em.emit("info", message=f"  story note: {issue}")

        # Collect the background worksheet.
        worksheet_md = ws_future.result()
        worksheet_path = run_dir / "worksheet.md"
        worksheet_path.write_text(worksheet_md, encoding="utf-8")
        db.update_run(run_id, worksheet_path=str(worksheet_path))
        em.emit(
            "worksheet",
            path=str(worksheet_path.relative_to(output_root)),
            title=lesson.unit_label,
        )

        # 5) Page rendering — strictly one page at a time, streamed live.
        # QA is PIPELINED: as soon as page N is drawn, its vision review is
        # submitted to a background thread while page N+1 renders, so the QA
        # phase costs almost nothing extra in wall-clock time.
        backend_label = (
            f"Nano Banana Pro ({image_quality})" if backend == "gemini"
            else f"{backend} backend"
        )
        _step(6, f"Drawing pages one by one via {backend_label}")
        n_scenes = len(storyboard.scenes)
        scenes_by_num = {s.number: s for s in storyboard.scenes}
        qa = StoryboardQAAgent(client) if run_qa else None
        qa_futures: dict[int, Any] = {}
        page_t0 = {"t": time.time()}

        def _on_panel(p) -> None:
            secs = time.time() - page_t0["t"]
            page_t0["t"] = time.time()
            svg_path = panels_dir / f"scene_{p.scene_number:02d}.svg"
            svg_path.write_text(p.svg, encoding="utf-8")
            em.emit(
                "panel",
                scene=p.scene_number,
                total=n_scenes,
                caption=p.caption,
                path=str(svg_path.relative_to(output_root)),
                secs=round(secs, 1),
            )
            if qa is not None:
                scene = scenes_by_num.get(p.scene_number)
                if scene is not None:
                    qa_futures[p.scene_number] = bg.submit(
                        qa.review,
                        scene=scene,
                        panel=p,
                        art_style=storyboard.art_style,
                        cast=storyboard.cast,
                    )

        panels, backend_obj = render_storyboard(
            storyboard,
            client,
            reference_paths=[],
            chain_panels=True,
            on_panel=_on_panel,
            on_status=lambda m: em.emit("warn", message=m),
            resolution=image_quality,
        )
        panels_by_num = {p.scene_number: p for p in panels}

        # 7) QA loop — collect the pipelined reviews (most are already done).
        qa_reports = []
        if run_qa:
            _step(
                7,
                f"Visual QA subagent reviewing ({resolved_provider} vision, "
                f"threshold {SETTINGS.qa_score_threshold})",
            )
            from curriculum_to_comic.qa import (
                PanelReview,
                is_review_error,
                needs_regeneration,
            )

            reviews_by_num: dict[int, Any] = {}
            for num in sorted(qa_futures):
                report = qa_futures[num].result()
                # A score-50 "review failed" report means the REVIEW call
                # broke, not the page — retry the review once before judging.
                if is_review_error(report):
                    em.emit(
                        "warn",
                        message=(
                            f"  page {num}: QA review call errored — "
                            "retrying the review"
                        ),
                    )
                    try:
                        report = qa.review(
                            scene=scenes_by_num[num],
                            panel=panels_by_num[num],
                            art_style=storyboard.art_style,
                            cast=storyboard.cast,
                        )
                    except Exception:
                        pass
                reviews_by_num[num] = PanelReview(
                    scene=scenes_by_num[num],
                    panel=panels_by_num[num],
                    report=report,
                )
                em.emit(
                    "qa",
                    scene=num,
                    verdict=report.verdict,
                    score=report.consistency_score,
                    issues=report.issues[:3],
                    retry=report.retry_count,
                )

            # one retry pass on panels that fail or score under the threshold
            failing = [
                r for r in reviews_by_num.values()
                if needs_regeneration(r.report)
            ]
            redraw_list = sorted(
                (r.scene.number, r.report.consistency_score) for r in failing
            )
            if redraw_list:
                em.emit(
                    "info",
                    message=(
                        "Auto-redraw triggered (score < "
                        f"{SETTINGS.qa_score_threshold} or fail): "
                        + ", ".join(f"page {n} ({s})" for n, s in redraw_list)
                    ),
                )
            else:
                em.emit(
                    "info",
                    message=(
                        f"All pages at or above the {SETTINGS.qa_score_threshold} "
                        "auto-redraw threshold"
                    ),
                )
            if failing:
                em.emit(
                    "warn",
                    message=(
                        f"QA: re-rendering {len(failing)} page(s) "
                        f"(fail verdict or score < {SETTINGS.qa_score_threshold})"
                    ),
                )
                for r in failing:
                    scene = scenes_by_num[r.scene.number]
                    hints = format_qa_suggestion_hint(r.report)
                    t_retry = time.time()
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
                    # KEEP-BETTER guard: never let a regenerated page replace
                    # the original if the redraw scored LOWER. A redraw that
                    # regresses is discarded so quality only ever ratchets up.
                    old_score = r.report.consistency_score
                    if new_report.consistency_score < old_score:
                        em.emit(
                            "info",
                            message=(
                                f"  page {scene.number}: redraw scored "
                                f"{new_report.consistency_score} < {old_score} "
                                "— keeping the original (no regression)"
                            ),
                        )
                        continue
                    reviews_by_num[scene.number] = PanelReview(
                        scene=scene, panel=new_panel, report=new_report
                    )
                    svg_path = panels_dir / f"scene_{scene.number:02d}.svg"
                    svg_path.write_text(new_panel.svg, encoding="utf-8")
                    em.emit(
                        "panel",
                        scene=scene.number,
                        total=n_scenes,
                        caption=new_panel.caption,
                        path=str(svg_path.relative_to(output_root)),
                        rerendered=True,
                        secs=round(time.time() - t_retry, 1),
                    )
                    em.emit(
                        "qa",
                        scene=scene.number,
                        verdict=new_report.verdict,
                        score=new_report.consistency_score,
                        issues=new_report.issues[:3],
                        retry=1,
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
            passed = sum(1 for r in qa_reports if r.verdict == "pass")
            warned = sum(1 for r in qa_reports if r.verdict == "warn")
            failed = sum(1 for r in qa_reports if r.verdict == "fail")
            avg = (
                sum(r.consistency_score for r in qa_reports) / len(qa_reports)
                if qa_reports else 0
            )
            em.emit(
                "info",
                message=(
                    f"QA summary: {passed} pass · {warned} warn · {failed} fail "
                    f"· avg score {avg:.0f}"
                ),
            )

            # ---- Book-level consistency review (all pages side by side) ----
            # Catches what per-page QA cannot: character drift, palette
            # shifts, garbled text, and broken page-to-page storytelling.
            from curriculum_to_comic.book_qa import (
                best_page_png,
                pages_to_regenerate,
                review_book,
            )

            em.emit(
                "info",
                message="Book reviewer judging all pages side by side "
                        "(consistency · accuracy · visual storytelling)…",
            )
            book_rep = review_book(storyboard, panels, client)
            if book_rep.error:
                em.emit("warn", message=f"Book review skipped: {book_rep.error}")
            else:
                em.emit(
                    "info",
                    message=(
                        f"Book consistency score: {book_rep.consistency_score} "
                        f"· best page: {book_rep.best_page} "
                        f"· {book_rep.summary[:160]}"
                    ),
                )
                flagged = pages_to_regenerate(book_rep)
                if flagged:
                    em.emit(
                        "warn",
                        message=(
                            f"Book QA: redrawing {len(flagged)} page(s) for "
                            f"cross-page consistency"
                        ),
                    )
                    anchor = best_page_png(book_rep, panels)
                    panels_map = {p.scene_number: p for p in panels}
                    reports_map = {r.scene_number: r for r in qa_reports}
                    for pr in flagged:
                        num = int(pr.get("page", 0) or 0)
                        scene = scenes_by_num.get(num)
                        if scene is None:
                            continue
                        hints = (
                            "BOOK CONSISTENCY FIXES (must apply): "
                            + (pr.get("regen_hints")
                               or "; ".join(pr.get("issues", [])[:4]))
                        )
                        if anchor is not None and hasattr(backend_obj, "_last_panel_png"):
                            # Anchor the redraw on the book's best page.
                            backend_obj._last_panel_png = anchor
                        t_r = time.time()
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
                                message=f"  page {num}: book-QA redraw failed ({exc})",
                            )
                            continue
                        new_report = qa.review(
                            scene=scene,
                            panel=new_panel,
                            art_style=storyboard.art_style,
                            cast=storyboard.cast,
                            retry_count=2,
                        )
                        new_report.retry_count = 2
                        # KEEP-BETTER guard: a book-QA redraw that scores lower
                        # than the page it replaces is discarded.
                        old_score = reports_map[num].consistency_score
                        if new_report.consistency_score < old_score:
                            em.emit(
                                "info",
                                message=(
                                    f"  page {num}: book redraw scored "
                                    f"{new_report.consistency_score} < {old_score} "
                                    "— keeping the original"
                                ),
                            )
                            continue
                        svg_path = panels_dir / f"scene_{num:02d}.svg"
                        svg_path.write_text(new_panel.svg, encoding="utf-8")
                        em.emit(
                            "panel",
                            scene=num,
                            total=n_scenes,
                            caption=new_panel.caption,
                            path=str(svg_path.relative_to(output_root)),
                            rerendered=True,
                            secs=round(time.time() - t_r, 1),
                        )
                        em.emit(
                            "qa",
                            scene=num,
                            verdict=new_report.verdict,
                            score=new_report.consistency_score,
                            issues=new_report.issues[:3],
                            retry=2,
                        )
                        panels_map[num] = new_panel
                        reports_map[num] = new_report
                        book_rep.regenerated_pages.append(num)
                    panels = [
                        panels_map[s.number]
                        for s in storyboard.scenes
                        if s.number in panels_map
                    ]
                    qa_reports = [
                        reports_map[s.number]
                        for s in storyboard.scenes
                        if s.number in reports_map
                    ]
                    (run_dir / "qa_reports.json").write_text(
                        _json.dumps(
                            [r.model_dump() for r in qa_reports], indent=2
                        ),
                        encoding="utf-8",
                    )
            (run_dir / "book_qa.json").write_text(
                _json.dumps(book_rep.to_dict(), indent=2), encoding="utf-8"
            )

        bg.shutdown(wait=False)

        # 8) Compile PDF.
        _step(8, "Compiling PDF comic book")
        pdf_path = run_dir / f"{_slug(lesson.title)}_comic.pdf"
        compile_pdf(
            pdf_path=pdf_path,
            lesson=lesson,
            storyboard=storyboard,
            panels=panels,
            qa_reports=qa_reports,
        )
        em.emit(
            "info",
            message=f"⏱ {_cur['label']} took {time.time() - _cur['t0']:.1f}s",
        )

        db.update_run(
            run_id,
            status="done",
            pdf_path=str(pdf_path),
            finished_at=db.now_ts(),
        )
        total_s = time.time() - run_t0
        em.emit(
            "done",
            pdf_path=str(pdf_path.relative_to(output_root)),
            worksheet_path=str(worksheet_path.relative_to(output_root)),
            run_dir=str(run_dir.relative_to(output_root)),
            message=f"Comic PDF + worksheet ready in {total_s/60:.1f} min",
        )

    except Exception as exc:  # pragma: no cover
        tb = traceback.format_exc()
        message = _friendly_error_message(exc)
        db.update_run(
            run_id, status="error", error=message, finished_at=db.now_ts()
        )
        em.emit("error", message=message, traceback=tb)


def _friendly_error_message(exc: Exception) -> str:
    """Turn nested SDK/retry errors into user-actionable Studio messages."""

    root = exc
    last_attempt = getattr(exc, "last_attempt", None)
    if last_attempt is not None:
        try:
            attempt_exc = last_attempt.exception()
        except Exception:
            attempt_exc = None
        if isinstance(attempt_exc, Exception):
            root = attempt_exc

    root_name = type(root).__name__
    root_text = str(root)
    if root_name == "AuthenticationError":
        return (
            "Claude authentication failed. Check your ANTHROPIC_API_KEY in "
            "`~/ComicTeach/.env`, save the file, then restart `python run_web.py`."
        )
    if "ANTHROPIC_API_KEY" in root_text:
        return (
            "ANTHROPIC_API_KEY is missing. Add it to `~/ComicTeach/.env`, "
            "then restart `python run_web.py`."
        )
    if "GEMINI_API_KEY" in root_text:
        return (
            "GEMINI_API_KEY is missing. Add it to `.env` (it is required for "
            "Nano Banana Pro image generation), then restart `python run_web.py`."
        )
    if root_name in {"PermissionDeniedError", "RateLimitError"}:
        return f"Claude API error ({root_name}): {root_text}"
    return root_text


# ---- per-page revision (teacher feedback after a finished run) ------------ #


def start_revision(
    *,
    run_id: str,
    scene_number: int,
    feedback: str,
    output_root: Path,
    provider: str = "auto",
    backend: str = "gemini",
    run_qa: bool = True,
) -> threading.Thread:
    """Re-draw ONE page of a finished run using the teacher's notes, re-QA
    it, and recompile the PDF. Events continue on the same run stream."""

    t = threading.Thread(
        target=_run_revision,
        name=f"c2c-rev-{run_id[:8]}",
        kwargs=dict(
            run_id=run_id,
            scene_number=scene_number,
            feedback=feedback,
            output_root=output_root,
            provider=provider,
            backend=backend,
            run_qa=run_qa,
        ),
        daemon=True,
    )
    t.start()
    return t


def _run_revision(
    *,
    run_id: str,
    scene_number: int,
    feedback: str,
    output_root: Path,
    provider: str,
    backend: str,
    run_qa: bool,
) -> None:
    em = _Emitter(run_id, start_seq=db.max_event_seq(run_id))
    db.update_run(run_id, status="running")
    os.environ["IMAGE_BACKEND"] = backend
    t_start = time.time()
    total = 3 if run_qa else 2

    try:
        import json as _json

        from curriculum_to_comic.compiler import compile_pdf
        from curriculum_to_comic.illustrator import get_backend
        from curriculum_to_comic.llm import get_text_client
        from curriculum_to_comic.models import (
            Lesson,
            Panel,
            PanelQAReport,
            Storyboard,
        )

        run = db.get_run(run_id)
        if not run or not run.get("run_dir"):
            raise RuntimeError("Run directory not found; cannot revise.")
        run_dir = Path(run["run_dir"])
        panels_dir = run_dir / "panels"
        storyboard = Storyboard.model_validate_json(
            (run_dir / "storyboard.json").read_text(encoding="utf-8")
        )
        lesson = Lesson.model_validate_json(
            (run_dir / "lesson.json").read_text(encoding="utf-8")
        )
        scenes_by_num = {s.number: s for s in storyboard.scenes}
        scene = scenes_by_num.get(scene_number)
        if scene is None:
            raise RuntimeError(f"Scene {scene_number} not found in this run.")

        em.emit(
            "step",
            step=1,
            total=total,
            label=f"Re-drawing page {scene_number} with your notes",
        )
        em.emit("info", message=f"Teacher notes: {feedback[:300]}")
        client = get_text_client(provider)

        # Reference images for consistency: built-in Doraemon style refs +
        # the neighboring page + the current version of this page.
        ref_paths: list[Path] = []
        if backend == "gemini":
            from curriculum_to_comic.image_backends.gemini_nano_banana import (
                _default_style_references,
            )
            from curriculum_to_comic.qa import _rasterize_svg_to_png

            ref_paths = list(_default_style_references())
            tmp_dir = panels_dir / "_refs"
            tmp_dir.mkdir(exist_ok=True)
            for num in (scene_number - 1, scene_number):
                f = panels_dir / f"scene_{num:02d}.svg"
                if not f.exists():
                    continue
                try:
                    png = _rasterize_svg_to_png(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                p = tmp_dir / f"ref_{num:02d}.png"
                p.write_bytes(png)
                ref_paths.append(p)

        backend_obj = get_backend(
            client, reference_paths=ref_paths, chain_panels=False
        )
        hints = (
            "TEACHER REVISION REQUEST — the teacher reviewed this page and "
            f"asked for these changes, which MUST be applied: {feedback}"
        )
        t0 = time.time()
        new_panel = backend_obj.render(
            scene, storyboard.art_style, storyboard.cast, extra_hints=hints
        )
        svg_path = panels_dir / f"scene_{scene_number:02d}.svg"
        svg_path.write_text(new_panel.svg, encoding="utf-8")
        em.emit(
            "panel",
            scene=scene_number,
            total=len(storyboard.scenes),
            caption=new_panel.caption,
            path=str(svg_path.relative_to(output_root)),
            rerendered=True,
            secs=round(time.time() - t0, 1),
        )

        # Load existing QA reports so the appendix stays complete.
        qa_reports: list = []
        qa_file = run_dir / "qa_reports.json"
        if qa_file.exists():
            try:
                qa_reports = [
                    PanelQAReport.model_validate(d)
                    for d in _json.loads(qa_file.read_text(encoding="utf-8"))
                ]
            except Exception:
                qa_reports = []

        if run_qa:
            em.emit("step", step=2, total=total, label="QA reviewing the revised page")
            from curriculum_to_comic.qa import StoryboardQAAgent

            qa_agent = StoryboardQAAgent(client)
            report = qa_agent.review(
                scene=scene,
                panel=new_panel,
                art_style=storyboard.art_style,
                cast=storyboard.cast,
                retry_count=1,
            )
            em.emit(
                "qa",
                scene=scene_number,
                verdict=report.verdict,
                score=report.consistency_score,
                issues=report.issues[:3],
                retry=1,
            )
            qa_reports = [r for r in qa_reports if r.scene_number != scene_number]
            qa_reports.append(report)
            qa_reports.sort(key=lambda r: r.scene_number)
            qa_file.write_text(
                _json.dumps([r.model_dump() for r in qa_reports], indent=2),
                encoding="utf-8",
            )

        em.emit("step", step=total, total=total, label="Recompiling PDF comic book")
        panels: list[Panel] = []
        for s in storyboard.scenes:
            if s.number == scene_number:
                panels.append(new_panel)
                continue
            f = panels_dir / f"scene_{s.number:02d}.svg"
            if not f.exists():
                continue
            panels.append(
                Panel(
                    scene_number=s.number,
                    svg=f.read_text(encoding="utf-8"),
                    caption=s.caption,
                    dialogue=s.dialogue,
                )
            )

        pdf_path = Path(run.get("pdf_path") or (run_dir / f"{_slug(lesson.title)}_comic.pdf"))
        compile_pdf(
            pdf_path=pdf_path,
            lesson=lesson,
            storyboard=storyboard,
            panels=panels,
            qa_reports=qa_reports,
        )

        db.update_run(
            run_id, status="done", pdf_path=str(pdf_path), finished_at=db.now_ts()
        )
        worksheet_rel = ""
        if run.get("worksheet_path"):
            try:
                worksheet_rel = str(
                    Path(run["worksheet_path"]).relative_to(output_root)
                )
            except ValueError:
                worksheet_rel = ""
        em.emit(
            "done",
            pdf_path=str(pdf_path.relative_to(output_root)),
            worksheet_path=worksheet_rel,
            run_dir=str(run_dir.relative_to(output_root)),
            message=(
                f"Page {scene_number} revised · PDF updated "
                f"({time.time() - t_start:.0f}s)"
            ),
        )

    except Exception as exc:  # pragma: no cover
        tb = traceback.format_exc()
        message = _friendly_error_message(exc)
        db.update_run(run_id, status="done", error=message)
        em.emit("error", message=f"Revision failed: {message}", traceback=tb)


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
    em.emit("step", step=1, total=8, label="Loading curriculum input")
    time.sleep(0.5)
    em.emit("step", step=2, total=8, label="Drafting lesson plan")
    time.sleep(0.7)
    em.emit("step", step=3, total=8, label="Writing student worksheet")
    time.sleep(0.5)
    em.emit("step", step=4, total=8, label="Writing 6-scene storyboard")
    time.sleep(0.7)
    em.emit("step", step=5, total=8, label="Story editor reviewing narrative flow")
    time.sleep(0.4)
    em.emit("info", message="[mock] Story flow score: 88 (kept)")
    em.emit("step", step=6, total=8, label="Drawing pages one by one (mock)")

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
                total=6,
                caption=captions[i - 1],
                path=str(dst.relative_to(output_root)),
            )
        time.sleep(0.4)

    em.emit("step", step=7, total=8, label="Visual QA subagent reviewing")
    for i in range(1, 7):
        em.emit("qa", scene=i, verdict="pass", score=88 + i, issues=[], retry=0)
        time.sleep(0.15)
    em.emit("step", step=8, total=8, label="Compiling PDF comic book")
    time.sleep(0.6)
    em.emit("info", message="[mock] All 6 pages passed QA (avg score 92)")
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
