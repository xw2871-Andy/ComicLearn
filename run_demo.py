"""Stdlib-only demo runner for ComicTeach.

The full pipeline lives in ``curriculum_to_comic/`` and depends on PyPI
packages (anthropic, pydantic, svglib, rich, tenacity). This demo bypasses
all of those by talking to the Anthropic REST API directly with urllib so
it can run inside the sandbox (which has no PyPI access).

It exercises:

    1. Lesson-plan generation (Claude)
    2. 6-scene storyboard generation (Claude)
    3. Six SVG comic panels (Claude)

It SKIPS the visual-QA subagent (needs svglib for rasterization) and PDF
compile (needs svglib + reportlab svg2rlg). Those run fine outside this
sandbox once you ``pip install -e .``.

Run::

    python run_demo.py "Riemann Sums" "AP Calculus AB"
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Load .env (stdlib parser, no python-dotenv dependency for portability).
ENV_PATH = Path(__file__).parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

# Reuse the project's prompts so the demo and the real agent stay in lockstep.
# We bypass the package __init__ (which pulls in pydantic/rich) and load
# prompts.py directly via importlib.
import importlib.util as _ilu
_pp = Path(__file__).parent / "curriculum_to_comic" / "prompts.py"
_spec = _ilu.spec_from_file_location("c2c_prompts", _pp)
_pmod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_pmod)
LESSON_PLANNER_SYSTEM = _pmod.LESSON_PLANNER_SYSTEM
STORYBOARD_SYSTEM = _pmod.STORYBOARD_SYSTEM
SVG_PANEL_SYSTEM = _pmod.SVG_PANEL_SYSTEM

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")


# --------------------------------------------------------------------------- #
# Anthropic call
# --------------------------------------------------------------------------- #


def claude(*, system: str, user: str, max_tokens: int = 4096, temperature: float = 0.4) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or "REPLACE_ME" in api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY in .env first.")

    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()

    req = urllib.request.Request(
        ANTHROPIC_ENDPOINT,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode())
                return "".join(b.get("text", "") for b in data.get("content", []))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:200] if exc.fp else ""
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Anthropic HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Network error: {exc}") from exc


def claude_json(*, system: str, user: str, max_tokens: int = 4096, temperature: float = 0.3) -> dict:
    raw = claude(system=system, user=user, max_tokens=max_tokens, temperature=temperature)
    return _parse_json_lenient(raw)


def _parse_json_lenient(raw: str) -> dict:
    raw = raw.strip()
    # Strip ```json fences if present.
    m = re.match(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if m:
        raw = m.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last-ditch: find the first {...} block.
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise
        return json.loads(m.group(0))


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def step1_lesson(topic: str, grade: str) -> dict:
    user = (
        f"# Lesson request\n\n"
        f"- Title: {topic}\n"
        f"- Grade level / course: {grade}\n"
        f"- Source type: topic\n\n"
        f"## Source material\n\n"
        f"(Topic-only mode — draw on canonical curricular knowledge.)\n\n"
        f"---\n\n"
        f"Produce the lesson plan JSON described in the system prompt. "
        f"Aim for 4-6 sections."
    )
    data = claude_json(system=LESSON_PLANNER_SYSTEM, user=user, max_tokens=3500, temperature=0.4)
    data.setdefault("title", topic)
    data.setdefault("grade_level", grade)
    return data


def step2_storyboard(lesson: dict, cast: list[str]) -> dict:
    cast_line = f"Cast: {', '.join(cast)}"
    lesson_json = json.dumps(lesson, indent=2, ensure_ascii=False)
    user = (
        "# Storyboard request\n\n"
        f"{cast_line}\n\n"
        "Convert the following lesson plan into a 6-scene comic storyboard "
        "following the system rules.\n\n"
        "## Lesson plan (JSON)\n\n"
        f"{lesson_json}\n\n"
        "Remember: output ONLY the storyboard JSON, no fences, no prose."
    )
    data = claude_json(system=STORYBOARD_SYSTEM, user=user, max_tokens=5500, temperature=0.7)
    data.setdefault("lesson_title", lesson.get("title", ""))
    data.setdefault("cast", cast)
    data["scenes"] = data.get("scenes", [])[:6]
    for i, s in enumerate(data["scenes"], 1):
        s["number"] = i
    return data


def step3_panels(storyboard: dict, out_dir: Path) -> list[dict]:
    panels_dir = out_dir / "panels"
    panels_dir.mkdir(exist_ok=True)
    panels = []
    art = storyboard.get("art_style", "Manga-style black-and-white comic")
    cast = storyboard.get("cast", ["Doraemon", "Nobita"])
    for scene in storyboard["scenes"]:
        dialogue = "\n".join(
            f"- {d['speaker']}: {d['text']}" for d in scene.get("dialogue", [])[:4]
        ) or "- (no dialogue)"
        math_line = (
            f"Holographic math overlay: {scene.get('holographic_math')}"
            if scene.get("holographic_math")
            else "No math overlay required."
        )
        user = (
            f"# Panel brief\n\n"
            f"Scene #{scene['number']}: \"{scene.get('title','')}\"\n"
            f"Pedagogical beat: {scene.get('pedagogical_beat','')}\n"
            f"Cast on screen: {', '.join(cast)}\n\n"
            f"Visual description:\n{scene.get('visual_description','')}\n\n"
            f"{math_line}\n\n"
            f"Dialogue lines to render as short speech bubbles (<=12 words each):\n"
            f"{dialogue}\n\n"
            f"Caption (optional narrator box, <=15 words): "
            f"{scene.get('caption') or '(none)'}\n\n"
            f"Art style: {art}\n\n"
            f"Now produce ONE SVG document (800x1000) following the system rules."
        )
        raw = claude(system=SVG_PANEL_SYSTEM, user=user, max_tokens=4096, temperature=0.6)
        m = re.search(r"<svg[\s\S]*?</svg>", raw, re.IGNORECASE)
        svg = m.group(0) if m else _fallback_svg(scene)
        (panels_dir / f"scene_{scene['number']:02d}.svg").write_text(svg, encoding="utf-8")
        panels.append({"scene_number": scene["number"], "svg": svg})
        print(f"  - scene {scene['number']} panel saved ({len(svg)} bytes)")
    return panels


def _fallback_svg(scene: dict) -> str:
    title = (scene.get("title") or f"Scene {scene['number']}").replace("&", "&amp;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000" '
        f'width="800" height="1000">'
        f'<rect width="800" height="1000" fill="#fef3c7"/>'
        f'<rect x="20" y="20" width="760" height="960" fill="#ffffff" '
        f'stroke="#111827" stroke-width="6"/>'
        f'<text x="400" y="500" text-anchor="middle" font-family="sans-serif" '
        f'font-size="36" fill="#111827">Scene {scene["number"]}</text>'
        f'<text x="400" y="560" text-anchor="middle" font-family="sans-serif" '
        f'font-size="22" fill="#374151">{title}</text>'
        f'</svg>'
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def slug(t: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in t.lower()).strip("_")[:60] or "lesson"


def main(topic: str, grade: str) -> None:
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(os.environ.get("DEFAULT_OUTPUT_DIR", "./outputs")) / "runs" / f"{ts}_{slug(topic)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== ComicTeach demo run ({MODEL}) ===")
    print(f"Topic: {topic}  |  Grade: {grade}")
    print(f"Run dir: {out_dir}\n")

    print("[1/3] Lesson plan...")
    lesson = step1_lesson(topic, grade)
    (out_dir / "lesson.json").write_text(json.dumps(lesson, indent=2, ensure_ascii=False))
    print(f"  -> {len(lesson.get('sections',[]))} sections, {len(lesson.get('learning_objectives',[]))} objectives\n")

    print("[2/3] Storyboard...")
    storyboard = step2_storyboard(lesson, cast=["Doraemon", "Nobita"])
    (out_dir / "storyboard.json").write_text(json.dumps(storyboard, indent=2, ensure_ascii=False))
    dialogue_lines = []
    for s in storyboard["scenes"]:
        dialogue_lines.append(f"# Scene {s['number']}: {s.get('title','')}")
        for d in s.get("dialogue", []):
            dialogue_lines.append(f"{d['speaker']}: {d['text']}")
        dialogue_lines.append("")
    (out_dir / "dialogue.txt").write_text("\n".join(dialogue_lines))
    print(f"  -> {len(storyboard['scenes'])} scenes, cast {storyboard.get('cast')}\n")

    print("[3/3] SVG panels (one Claude call per scene)...")
    panels = step3_panels(storyboard, out_dir)
    print(f"  -> {len(panels)} panel SVGs\n")

    summary = {
        "topic": topic, "grade": grade, "run_dir": str(out_dir),
        "lesson_title": lesson.get("title"),
        "panel_count": len(panels),
    }
    (out_dir / "book.json").write_text(json.dumps(summary, indent=2))
    print(f"DONE -> {out_dir}")


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Introducing the Limit"
    grade = sys.argv[2] if len(sys.argv) > 2 else "AP Calculus AB"
    main(topic, grade)
