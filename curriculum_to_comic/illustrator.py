"""Step 3: Render each :class:`Scene` as a comic panel.

Two backends ship today:

- ``svg``: Claude authors raw SVG vector art (free, no extra API key).
- ``gemini``: Google Nano Banana 2 (``gemini-3.1-flash-image-preview``) produces
  photorealistic anime panels and supports reference-image conditioning for
  visual consistency across all 6 panels of a comic.

Other backends (OpenAI gpt-image, Replicate SDXL) are placeholders for future
work behind the same :class:`IllustratorBackend` protocol.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Protocol

from .claude_client import ClaudeClient
from .config import SETTINGS
from .models import Panel, Scene, Storyboard
from .prompts import SVG_PANEL_SYSTEM


class IllustratorBackend(Protocol):
    def render(
        self,
        scene: Scene,
        art_style: str,
        cast: list[str],
        *,
        extra_hints: str | None = None,
    ) -> Panel: ...


# --------------------------------------------------------------------------- #
# Default backend: Claude-authored SVG.
# --------------------------------------------------------------------------- #


class ClaudeSVGBackend:
    def __init__(self, claude: ClaudeClient, model: str | None = None) -> None:
        self._claude = claude
        self._model = model or SETTINGS.visual_model

    def render(
        self,
        scene: Scene,
        art_style: str,
        cast: list[str],
        *,
        extra_hints: str | None = None,
    ) -> Panel:
        user_msg = _format_panel_brief(
            scene, art_style=art_style, cast=cast, extra_hints=extra_hints
        )
        raw = self._claude.complete(
            system=SVG_PANEL_SYSTEM,
            user=user_msg,
            model=self._model,
            max_tokens=4096,
            temperature=0.6,
        )
        svg = _extract_svg(raw) or _fallback_svg(scene)
        return Panel(
            scene_number=scene.number,
            svg=svg,
            caption=scene.caption,
            dialogue=scene.dialogue,
        )


def _format_panel_brief(
    scene: Scene,
    *,
    art_style: str,
    cast: list[str],
    extra_hints: str | None = None,
) -> str:
    dialogue_block = "\n".join(
        f"- {d.speaker}: {d.text}" for d in scene.dialogue[:4]
    ) or "- (no dialogue)"
    math_line = (
        f"Holographic math overlay: {scene.holographic_math}"
        if scene.holographic_math
        else "No math overlay required."
    )
    hint_block = (
        f"\n\nREVISION NOTES (from QA review, must address):\n{extra_hints}"
        if extra_hints
        else ""
    )
    return textwrap.dedent(
        f"""
        # Panel brief

        Scene #{scene.number}: "{scene.title}"
        Pedagogical beat: {scene.pedagogical_beat}
        Cast on screen: {', '.join(cast)}

        Visual description:
        {scene.visual_description}

        {math_line}

        Up to 3 of these lines should appear as short speech bubbles (truncate to <=12 words each):
        {dialogue_block}

        Caption (optional narrator box, <=15 words): {scene.caption or "(none)"}

        Art style: {art_style}{hint_block}

        Now produce ONE SVG document (800x1000) following the system rules.
        """
    ).strip()


_SVG_RE = re.compile(r"<svg[\s\S]*?</svg>", re.IGNORECASE)


def _extract_svg(raw: str) -> str | None:
    """Grab the first <svg>...</svg> block from a possibly-noisy response."""

    if not raw:
        return None
    m = _SVG_RE.search(raw)
    return m.group(0) if m else None


def _fallback_svg(scene: Scene) -> str:
    """Minimal placeholder so the pipeline never hard-fails."""

    safe_title = (scene.title or f"Scene {scene.number}").replace("&", "&amp;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000" '
        f'width="800" height="1000">'
        f'<rect width="800" height="1000" fill="#fef3c7"/>'
        f'<rect x="20" y="20" width="760" height="960" fill="#ffffff" '
        f'stroke="#111827" stroke-width="6"/>'
        f'<text x="400" y="500" text-anchor="middle" font-family="sans-serif" '
        f'font-size="36" fill="#111827">Scene {scene.number}</text>'
        f'<text x="400" y="560" text-anchor="middle" font-family="sans-serif" '
        f'font-size="22" fill="#374151">{safe_title}</text>'
        f"</svg>"
    )


# --------------------------------------------------------------------------- #
# Public factory.
# --------------------------------------------------------------------------- #


def get_backend(
    claude: ClaudeClient,
    *,
    reference_paths: list[Path] | None = None,
    chain_panels: bool = True,
) -> IllustratorBackend:
    """Return the configured backend, honoring ``IMAGE_BACKEND``.

    ``reference_paths`` and ``chain_panels`` are only consumed by image-API
    backends (currently the Gemini one); the SVG backend ignores them.
    """

    backend = SETTINGS.image_backend
    if backend == "svg":
        return ClaudeSVGBackend(claude)
    if backend in {"gemini", "nano-banana", "nano_banana"}:
        # Imported lazily so users without a Gemini key never hit this code path.
        from .image_backends.gemini_nano_banana import GeminiNanoBananaBackend

        return GeminiNanoBananaBackend(
            reference_paths=reference_paths or [],
            chain_panels=chain_panels,
        )
    raise NotImplementedError(
        f"IMAGE_BACKEND={backend!r} is not implemented yet. "
        "Supported values: 'svg' (default, no extra API), "
        "'gemini' (Google Nano Banana 2 via GEMINI_API_KEY)."
    )


def render_storyboard(
    storyboard: Storyboard,
    claude: ClaudeClient,
    *,
    reference_paths: list[Path] | None = None,
    chain_panels: bool = True,
) -> tuple[list[Panel], IllustratorBackend]:
    """Render every scene and return ``(panels, backend)``.

    The backend is returned so callers (e.g. the QA-driven retry loop in the
    orchestrator) can call ``backend.render(...)`` again on individual scenes
    without having to re-instantiate it.
    """

    backend = get_backend(
        claude,
        reference_paths=reference_paths,
        chain_panels=chain_panels,
    )
    panels: list[Panel] = []
    for scene in storyboard.scenes:
        panels.append(backend.render(scene, storyboard.art_style, storyboard.cast))
    return panels, backend
