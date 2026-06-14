"""Google Nano Banana Pro (Gemini 3 Pro Image) backend.

This backend uses the public REST endpoint so we don't take a hard dependency
on the ``google-genai`` SDK. Each call returns a base64 image which we embed
inside a 1-element <svg> wrapper so the compiler's SVG layout path can render
it unchanged.

Sequential, one-page-at-a-time generation
-----------------------------------------
Pages are ALWAYS generated strictly one by one — never in parallel. Each
request waits for the previous page to finish so the next request can include
it as a reference. This is deliberate: it keeps page quality high and the
art style/character designs consistent across the whole book.

Visual-consistency strategy
---------------------------
Three flavors of reference image are passed to Gemini as ``inlineData`` parts
on every page request:

1. **Built-in Doraemon style references.** Real Doraemon-manga sample pages
   shipped in ``samples/references/`` are attached by default so every page
   anchors to the authentic full-color Doraemon manga look (the quality bar).
2. **User-supplied references** (``--reference path.png`` on the CLI,
   repeatable). Prepended to every request when provided.
3. **Rolling self-reference.** After we render page N, we cache its bytes and
   pass them to page N+1's request. This stops the model from drifting
   between scenes (e.g. swapping a "futuristic math lab" for a "cottage").

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
from ..prompts import IMAGE_LAYOUT_ANCHOR, IMAGE_STYLE_ANCHOR, load_tuning

GEMINI_ENDPOINT_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

# Cap on how many reference images we attach per request. Nano Banana Pro
# accepts up to 14 inline images; we stay below to leave headroom for the
# prompt itself and to keep latency sane.
MAX_REFS_PER_REQUEST = 6

# Authentic character bible distilled from the sample Doraemon pages.
# Explicit palette + proportions because cross-page palette/proportion drift
# was the dominant book-QA failure across the chapter marathon.
CHARACTER_ANCHOR = (
    "Authentic Doraemon manga character designs, IDENTICAL on every page: "
    "Doraemon is the classic round blue robot cat (bright sky-blue body ~#1BA7DC, "
    "pure white face and belly, RED collar with a GOLD bell, red round nose, "
    "six whiskers, short stubby limbs, no neck, 4D pocket on his belly). "
    "Nobita is a small boy with round black glasses, short black hair, fair "
    "skin, yellow short-sleeve shirt and blue shorts. Keep their proportions, "
    "face shapes, line weight, and exact colors locked to the reference pages — "
    "do NOT restyle, age, or re-proportion them between panels. If supporting "
    "characters appear (Gian: big, tan shirt; Suneo: pointy hair; Mom), they "
    "must NOT change Doraemon's or Nobita's established design."
)

QUALITY_ANCHOR = (
    "Render at professional published-manga quality: crisp clean line art, "
    "rich flat cel colors with soft shading, detailed backgrounds, white "
    "page margins, and a small page number at the bottom corner. All speech "
    "bubble text must be perfectly spelled, in English, and easily readable. "
    "Show at most 3-4 speech bubbles total on the page, each 1-2 short lines — "
    "never crammed. Render the holographic math overlay as ONE clean, large, "
    "correctly-spaced formula per panel — do NOT dump dense worksheet-style "
    "definition boxes with tiny unreadable text. Keep the same physical "
    "setting flowing from the previous page unless the story moves the "
    "characters for a clear reason."
)


class GeminiNanoBananaBackend:
    """Renders one scene per call via Nano Banana Pro (Gemini 3 Pro Image).

    Parameters
    ----------
    api_key:
        Google AI Studio key. Defaults to ``GEMINI_API_KEY`` from the env.
    reference_paths:
        Optional list of comic-page / character-sheet image paths. These are
        loaded once at init time and re-sent with EVERY page request so the
        model keeps a consistent style, palette, and character design. When
        empty, the built-in Doraemon style references are used.
    chain_panels:
        When True (default), the most recently generated page is also passed
        as a reference for the next page. This is the "rolling consistency"
        trick from the original DoraeMath pipeline.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        reference_paths: Iterable[Path] | None = None,
        chain_panels: bool = True,
        resolution: str | None = None,
    ) -> None:
        self._api_key = api_key or SETTINGS.gemini_api_key
        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your environment / .env. "
                "It is required for Nano Banana Pro image generation."
            )
        self._model = SETTINGS.gemini_image_model
        # Per-run quality: "1K" (draft, ~2x faster/cheaper), "2K" (standard,
        # matches the sample Doraemon pages), "4K" (print).
        self._resolution = (resolution or SETTINGS.gemini_image_resolution).upper()
        if self._resolution not in {"1K", "2K", "4K"}:
            self._resolution = "2K"
        self._user_refs: list[tuple[bytes, str]] = []
        ref_list = [Path(p) for p in (reference_paths or [])]
        if not ref_list:
            ref_list = _default_style_references()
        for p in ref_list:
            try:
                data = Path(p).read_bytes()
            except OSError:
                continue
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
            f'- {d.speaker}: "{_shorten(d.text)}"' for d in scene.dialogue[:3]
        )
        math_overlay = (
            f"Include a glowing holographic math overlay rendered clearly and "
            f"with exactly correct notation: {scene.holographic_math}. "
            if scene.holographic_math
            else ""
        )
        caption_line = (
            f'Narrator caption box: "{scene.caption}". ' if scene.caption else ""
        )
        hint_block = (
            f" REVISION NOTES (from QA reviewer, must be addressed): "
            f"{extra_hints}"
            if extra_hints
            else ""
        )
        return (
            f"{IMAGE_STYLE_ANCHOR} {art_style} "
            f"{IMAGE_LAYOUT_ANCHOR} "
            f"{CHARACTER_ANCHOR} "
            f"{QUALITY_ANCHOR} "
            f"Maintain STRICT visual consistency with the reference images "
            f"provided: same character designs, same color palette, same "
            f"linework, same overall aesthetic. This is page {scene.number} "
            f"of a 6-page comic lesson. "
            f"Characters on this page: {', '.join(cast)}. "
            f"Scene: {scene.visual_description}. "
            f"{math_overlay}{caption_line}"
            f"Include up to 3 short comic speech bubbles, each max 1-2 short "
            f"sentences, no duplicated lines between characters:\n"
            f"{dialogue_block}\n"
            f"Educational tone, age-appropriate, no extra text outside "
            f"bubbles and the math overlay."
            f"{hint_block}"
            f"{load_tuning('image')}"
        ).strip()

    # ---- HTTP --------------------------------------------------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _call_gemini(
        self, prompt: str, *, references: list[tuple[bytes, str]] | None = None
    ) -> bytes:
        endpoint = GEMINI_ENDPOINT_TMPL.format(model=self._model)
        url = f"{endpoint}?key={self._api_key}"

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
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": "4:5",
                    "imageSize": self._resolution,
                },
            },
        }
        try:
            return self._post(url, payload)
        except RuntimeError as exc:
            # Defensive: some preview endpoints reject imageConfig fields.
            # Retry once without it rather than failing the page.
            if "HTTP 400" in str(exc) and "imageConfig" in json.dumps(payload):
                payload["generationConfig"] = {"responseModalities": ["IMAGE"]}
                return self._post(url, payload)
            raise

    def _post(self, url: str, payload: dict[str, Any]) -> bytes:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # surface API error body
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise RuntimeError(
                f"Gemini API HTTP {exc.code} ({self._model}): {detail[:400]}"
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


def _default_style_references(limit: int = 3) -> list[Path]:
    """Built-in Doraemon style reference pages shipped with the repo."""

    ref_dir = Path(__file__).resolve().parents[2] / "samples" / "references"
    if not ref_dir.is_dir():
        return []
    refs = sorted(ref_dir.glob("doraemon_style_ref*"))
    if not refs:
        refs = sorted(ref_dir.glob("doraemon_teach_limit_page*"))
    return refs[:limit]


def _shorten(text: str, max_words: int = 14) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"


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
