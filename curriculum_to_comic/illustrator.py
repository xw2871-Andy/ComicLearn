"""Step 3: Render each :class:`Scene` as a comic page.

Two backends ship today:

- ``gemini`` (default): Google Nano Banana Pro (``gemini-3-pro-image``)
  produces publication-quality manga pages and supports reference-image
  conditioning for visual consistency across all 6 pages of a comic.
- ``svg``: the text model authors raw SVG vector art (free, no image credits).

Pages are rendered strictly ONE BY ONE — each page waits for the previous
page so it can be passed as a rolling reference. Never parallelize this.
"""

from __future__ import annotations

import os
import re
import textwrap
import time
from pathlib import Path
from typing import Callable, Protocol

from .config import SETTINGS
from .models import Panel, Scene, Storyboard
from .prompts import SVG_PANEL_SYSTEM


def _render_with_retry(
    backend: "IllustratorBackend",
    scene: Scene,
    art_style: str,
    cast: list[str],
    *,
    on_status: Callable[[str], None] | None = None,
) -> Panel:
    """Render one page, surviving TRANSIENT failures (network blips, brief
    API 5xx/outage) with exponential backoff.

    The image backend already does a few fast internal retries; this adds an
    OUTER layer with longer sleeps so a multi-second outage doesn't discard
    the whole chapter's completed lesson/worksheet/storyboard work. Tunable
    via ``C2C_RENDER_RETRIES`` (default 4) and ``C2C_RENDER_BACKOFF`` seconds
    (default 20, doubled each attempt)."""

    attempts = max(1, int(os.getenv("C2C_RENDER_RETRIES", "4")))
    backoff = float(os.getenv("C2C_RENDER_BACKOFF", "20"))
    last_exc: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return backend.render(scene, art_style, cast)
        except Exception as exc:  # transient network/API failure
            last_exc = exc
            if i >= attempts:
                break
            wait = backoff * (2 ** (i - 1))
            if on_status:
                on_status(
                    f"page {scene.number}: render attempt {i}/{attempts} "
                    f"failed ({type(exc).__name__}); retrying in {wait:.0f}s"
                )
            time.sleep(wait)
    raise RuntimeError(
        f"page {scene.number} render failed after {attempts} attempts: "
        f"{type(last_exc).__name__}: {last_exc}"
    ) from last_exc


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
# SVG backend: text model authors vector art.
# --------------------------------------------------------------------------- #


class ClaudeSVGBackend:
    """SVG vector panels authored by the configured text model
    (Claude or Gemini — both expose ``complete``)."""

    def __init__(self, client, model: str | None = None) -> None:
        self._client = client
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
        kwargs = dict(
            system=SVG_PANEL_SYSTEM,
            user=user_msg,
            max_tokens=4096,
            temperature=0.6,
        )
        # Only pass the Anthropic model override to the Anthropic client.
        if type(self._client).__name__ == "ClaudeClient":
            kwargs["model"] = self._model
        raw = self._client.complete(**kwargs)
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
    client,
    *,
    reference_paths: list[Path] | None = None,
    chain_panels: bool = True,
    resolution: str | None = None,
) -> IllustratorBackend:
    """Return the configured backend, honoring ``IMAGE_BACKEND``.

    ``reference_paths`` and ``chain_panels`` are only consumed by image-API
    backends (currently the Gemini one); the SVG backend ignores them.
    """

    # Read the live env first: the web runner switches backends per run by
    # setting IMAGE_BACKEND after SETTINGS was frozen at import time.
    import os

    backend = os.getenv("IMAGE_BACKEND", SETTINGS.image_backend).lower()
    if backend == "svg":
        return ClaudeSVGBackend(client)
    if backend in {"gemini", "nano-banana", "nano_banana", "nano-banana-pro"}:
        # Imported lazily so users without a Gemini key never hit this code path.
        from .image_backends.gemini_nano_banana import GeminiNanoBananaBackend

        return GeminiNanoBananaBackend(
            reference_paths=reference_paths or [],
            chain_panels=chain_panels,
            resolution=resolution,
        )
    raise NotImplementedError(
        f"IMAGE_BACKEND={backend!r} is not implemented yet. "
        "Supported values: 'gemini' (Nano Banana Pro via GEMINI_API_KEY, "
        "default) and 'svg' (vector panels, no extra API)."
    )


def render_storyboard(
    storyboard: Storyboard,
    client,
    *,
    reference_paths: list[Path] | None = None,
    chain_panels: bool = True,
    on_panel: Callable[[Panel], None] | None = None,
    on_status: Callable[[str], None] | None = None,
    resolution: str | None = None,
) -> tuple[list[Panel], IllustratorBackend]:
    """Render every scene SEQUENTIALLY and return ``(panels, backend)``.

    Pages are generated one at a time, in scene order, so each request can
    carry the previous page as a consistency reference. ``on_panel`` is
    invoked after each page completes (used by the web runner to stream
    per-page progress to the browser).

    The backend is returned so callers (e.g. the QA-driven retry loop in the
    orchestrator) can call ``backend.render(...)`` again on individual scenes
    without having to re-instantiate it.
    """

    backend = get_backend(
        client,
        reference_paths=reference_paths,
        chain_panels=chain_panels,
        resolution=resolution,
    )
    panels: list[Panel] = []
    for scene in storyboard.scenes:
        panel = _render_with_retry(
            backend,
            scene,
            storyboard.art_style,
            storyboard.cast,
            on_status=on_status,
        )
        panels.append(panel)
        if on_panel is not None:
            on_panel(panel)
    return panels, backend
