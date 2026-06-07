"""Google Gemini 3.1 Flash Image Preview (aka 'Nano Banana 2') backend.

This backend uses the public REST endpoint so we don't take a hard dependency
on the ``google-genai`` SDK. Each call returns a base64 PNG which we embed
inside a 1-element <svg> wrapper so the compiler's SVG layout path can render
it unchanged.

Visual-consistency strategy
---------------------------
Two flavors of reference image are passed to Gemini as ``inlineData`` parts on
every panel request, exactly the way Andy's original
``gemini_image_gen_template.js`` did it:

1. **User-supplied references** (``--reference path.png`` on the CLI, repeatable).
   These are loaded once at construction time and prepended to every request so
   the model anchors every panel to the same character designs / palette.
2. **Rolling self-reference.** After we render panel N, we cache its PNG bytes
   and pass them to panel N+1's request. This stops the model from drifting
   between scenes (e.g. swapping a "futuristic math lab" for a "cottage").

The mime type for every reference is sniffed from the first few bytes so PNG
and JPEG references both work.

Docs: https://ai.google.dev/gemini-api/docs/image-generation
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from html import escape
from pathlib import Path
from typing import Any, Iterable

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import SETTINGS
from ..models import Panel, Scene

GEMINI_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Cap on how many reference images we attach per request. The Nano Banana 2
# preview accepts up to 14 inline images; we stay below to leave headroom for
# the prompt itself and to keep latency sane.
MAX_REFS_PER_REQUEST = 6


class GeminiNanoBananaBackend:
    """Renders one scene per call via Gemini 3.1 Flash Image Preview.

    Parameters
    ----------
    api_key:
        Google AI Studio key. Defaults to ``GEMINI_API_KEY`` from the env.
    reference_paths:
        Optional list of comic-page / character-sheet image paths. These are
        loaded once at init time and re-sent with EVERY panel request so the
        model keeps a consistent style, palette, and character design.
    chain_panels:
        When True (default), the most recently generated panel is also passed
        as a reference for the next panel. This is the "rolling consistency"
        trick from the original DoraeMath pipeline.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        reference_paths: Iterable[Path] | None = None,
        chain_panels: bool = True,
    ) -> None:
        self._api_key = api_key or SETTINGS.gemini_api_key
        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Either set it in your environment / "
                ".env or switch IMAGE_BACKEND back to 'svg'."
            )
        self._user_refs: list[tuple[bytes, str]] = []
        for p in reference_paths or []:
            data = Path(p).read_bytes()
            self._user_refs.append((data, _sniff_mime(data)))
        self._chain_panels = chain_panels
        self._last_panel_png: bytes | None = None

    # ---- IllustratorBackend protocol ---------------------------------- #

    def render(
        self,
        scene: Scene,
        art_style: str,
        cast: list[str],
        *,
        extra_hints: str | None = None,
    ) -> Panel:
        prompt = self._build_prompt(
            scene, art_style=art_style, cast=cast, extra_hints=extra_hints
        )
        refs = list(self._user_refs)
        if self._chain_panels and self._last_panel_png is not None:
            refs.append((self._last_panel_png, "image/png"))
        refs = refs[-MAX_REFS_PER_REQUEST:]

        png_bytes = self._call_gemini(prompt, references=refs)
        # Cache for the next scene's rolling reference.
        self._last_panel_png = png_bytes

        svg = self._wrap_png_in_svg(base64.b64encode(png_bytes).decode("ascii"))
        return Panel(
            scene_number=scene.number,
            svg=svg,
            caption=scene.caption,
            dialogue=scene.dialogue,
        )

    # ---- Prompt assembly --------------------------------------------- #

    @staticmethod
    def _build_prompt(
        scene: Scene,
        *,
        art_style: str,
        cast: list[str],
        extra_hints: str | None = None,
    ) -> str:
        dialogue_block = "\n".join(
            f'- {d.speaker}: "{d.text}"' for d in scene.dialogue[:3]
        )
        math_overlay = (
            f"Include a holographic math overlay rendered clearly: "
            f"{scene.holographic_math}"
            if scene.holographic_math
            else ""
        )
        hint_block = (
            f" REVISION NOTES (from QA reviewer, must be addressed): "
            f"{extra_hints}"
            if extra_hints
            else ""
        )
        return (
            f"{art_style} "
            f"MULTI-PANEL comic page layout: At least 3 vertical rows, mixing "
            f"single wide panels and side-by-side double panels. Clean white "
            f"margins and professional comic gutters between panels. "
            f"Maintain STRICT visual consistency with the reference images "
            f"provided: same character designs, same color palette, same "
            f"linework, same overall aesthetic. "
            f"Characters: {', '.join(cast)}. "
            f"Scene: {scene.visual_description}. "
            f"{math_overlay} "
            f"Include up to 3 short comic speech bubbles, each with one short "
            f"line of dialogue (max 12 words):\n{dialogue_block}\n"
            f"Educational tone, age-appropriate, no extra text outside bubbles."
            f"{hint_block}"
        ).strip()

    # ---- HTTP --------------------------------------------------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _call_gemini(
        self, prompt: str, *, references: list[tuple[bytes, str]] | None = None
    ) -> bytes:
        url = f"{GEMINI_ENDPOINT}?key={self._api_key}"

        parts: list[dict[str, Any]] = [{"text": prompt}]
        for blob, mime in references or []:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": mime,
                        "data": base64.b64encode(blob).decode("ascii"),
                    }
                }
            )

        payload: dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # surface API error body
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise RuntimeError(
                f"Gemini API HTTP {exc.code}: {detail[:400]}"
            ) from exc
        return self._extract_png_bytes(data)

    @staticmethod
    def _extract_png_bytes(data: dict[str, Any]) -> bytes:
        try:
            for part in data["candidates"][0]["content"]["parts"]:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and "data" in inline:
                    return base64.b64decode(inline["data"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected Gemini response shape: {json.dumps(data)[:400]}"
            ) from exc
        raise RuntimeError(
            f"No inline image data in Gemini response: {json.dumps(data)[:400]}"
        )

    # ---- SVG wrapping (so PDF compiler stays uniform) ---------------- #

    @staticmethod
    def _wrap_png_in_svg(png_b64: str) -> str:
        """Embed a base64 PNG inside an 800x1000 SVG document."""

        data_uri = f"data:image/png;base64,{escape(png_b64)}"
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'viewBox="0 0 800 1000" width="800" height="1000">'
            f'<image x="0" y="0" width="800" height="1000" '
            f'preserveAspectRatio="xMidYMid meet" href="{data_uri}"/>'
            "</svg>"
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _sniff_mime(data: bytes) -> str:
    """Return an HTTP mime type for a small set of common image formats."""

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/png"
