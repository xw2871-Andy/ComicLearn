"""Gemini text/vision client with the same interface as :class:`ClaudeClient`.

This lets every pipeline step (lesson plan, worksheet, storyboard, QA vision
review) run on either Anthropic or Gemini, selected per run. It uses the
public REST endpoint so we don't take a hard dependency on ``google-genai``.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from .claude_client import _parse_json_lenient
from .config import SETTINGS

_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiTextClient:
    """Duck-typed twin of :class:`ClaudeClient` backed by the Gemini API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        import os

        self._api_key = api_key or SETTINGS.require_gemini()
        self._model = model or SETTINGS.gemini_text_model
        # Used automatically when the primary model is unavailable
        # (e.g. "User location is not supported", model NOT_FOUND).
        self._fallback_model = os.getenv(
            "GEMINI_FALLBACK_TEXT_MODEL", "gemini-2.5-flash"
        )

    # ----- text ------------------------------------------------------------ #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        parts: list[dict[str, Any]] = [{"text": user}]
        return self._generate(
            system=system,
            parts=parts,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        raw = self.complete(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        try:
            return _parse_json_lenient(raw)
        except ValueError:
            repaired = self.complete(
                system=(
                    "You repair malformed model output into one complete, valid "
                    "JSON object. Return only JSON. Do not use markdown fences. "
                    "Preserve all existing fields and complete any truncated "
                    "arrays or strings with reasonable concise values."
                ),
                user=(
                    "The previous response was supposed to be JSON for this "
                    "task, but it was malformed or truncated.\n\n"
                    "Original task prompt:\n"
                    f"{user}\n\n"
                    "Malformed response:\n"
                    f"{raw}\n\n"
                    "Return one complete valid JSON object now."
                ),
                model=model,
                max_tokens=max(max_tokens, 6000),
                temperature=0,
            )
            return _parse_json_lenient(repaired)

    # ----- vision (QA subagent) -------------------------------------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def complete_with_image(
        self,
        *,
        system: str,
        user_text: str,
        image_bytes: bytes,
        media_type: str = "image/png",
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        parts: list[dict[str, Any]] = [
            {
                "inlineData": {
                    "mimeType": media_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }
            },
            {"text": user_text},
        ]
        return self._generate(
            system=system,
            parts=parts,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def complete_with_images(
        self,
        *,
        system: str,
        user_text: str,
        images: list[bytes],
        media_type: str = "image/png",
        model: str | None = None,
        max_tokens: int = 3000,
        temperature: float = 0.2,
    ) -> str:
        """Multimodal completion with MANY images (labeled Page 1..N)."""

        parts: list[dict[str, Any]] = []
        for i, img in enumerate(images, start=1):
            parts.append({"text": f"Page {i}:"})
            parts.append(
                {
                    "inlineData": {
                        "mimeType": media_type,
                        "data": base64.b64encode(img).decode("ascii"),
                    }
                }
            )
        parts.append({"text": user_text})
        return self._generate(
            system=system,
            parts=parts,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def complete_json_with_images(
        self,
        *,
        system: str,
        user_text: str,
        images: list[bytes],
        media_type: str = "image/png",
        model: str | None = None,
        max_tokens: int = 3000,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        raw = self.complete_with_images(
            system=system,
            user_text=user_text,
            images=images,
            media_type=media_type,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return _parse_json_lenient(raw)

    def complete_json_with_image(
        self,
        *,
        system: str,
        user_text: str,
        image_bytes: bytes,
        media_type: str = "image/png",
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        raw = self.complete_with_image(
            system=system,
            user_text=user_text,
            image_bytes=image_bytes,
            media_type=media_type,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        try:
            return _parse_json_lenient(raw)
        except ValueError:
            return _parse_json_lenient(self._repair_json(raw))

    def _repair_json(self, raw: str) -> str:
        """Text-only second pass that completes truncated/malformed JSON."""

        return self.complete(
            system=(
                "You repair malformed model output into one complete, valid "
                "JSON object. Return only JSON. Do not use markdown fences. "
                "Preserve all existing fields and complete any truncated "
                "arrays or strings with reasonable concise values."
            ),
            user=(
                "This response was supposed to be one JSON object but is "
                f"malformed or truncated:\n\n{raw}\n\n"
                "Return the complete valid JSON object now."
            ),
            max_tokens=3000,
            temperature=0,
        )

    # ----- HTTP ------------------------------------------------------------- #

    def _generate(
        self,
        *,
        system: str,
        parts: list[dict[str, Any]],
        model: str | None,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Call generateContent with two built-in self-heals:

        1. **Truncation** — Gemini 3.x spends output budget on internal
           thinking; if the response stops with finishReason MAX_TOKENS the
           call is retried with a doubled budget (up to 16K).
        2. **Model unavailability** — "User location is not supported" /
           FAILED_PRECONDITION / NOT_FOUND errors automatically fall back to
           ``GEMINI_FALLBACK_TEXT_MODEL`` (default gemini-2.5-flash).
        """

        mdl = model or self._model
        # Generous floor: thinking models eat into the visible-output budget.
        budget = max(max_tokens, 3000)

        for _attempt in range(4):
            payload: dict[str, Any] = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {
                    "maxOutputTokens": budget,
                    "temperature": temperature,
                },
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{_API_ROOT}/{mdl}:generateContent?key={self._api_key}",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=240) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                unavailable = (
                    "User location is not supported" in detail
                    or "FAILED_PRECONDITION" in detail
                    or '"NOT_FOUND"' in detail
                )
                if unavailable and mdl != self._fallback_model:
                    mdl = self._fallback_model  # retry on the fallback model
                    continue
                raise RuntimeError(
                    f"Gemini API HTTP {exc.code} ({mdl}): {detail[:400]}"
                ) from exc

            text, finish = _extract_text_and_finish(data)
            if finish == "MAX_TOKENS" and budget < 16000:
                budget *= 2  # truncated mid-answer: retry with more room
                continue
            if text:
                return text
            raise RuntimeError(
                f"Unexpected Gemini response shape ({mdl}): "
                f"{json.dumps(data)[:400]}"
            )
        raise RuntimeError(
            f"Gemini response stayed truncated after retries ({mdl})."
        )


def _extract_text_and_finish(data: dict[str, Any]) -> tuple[str, str]:
    """Return (text, finishReason) — empty text when no text parts exist."""

    finish = ""
    try:
        cand = data["candidates"][0]
        finish = str(cand.get("finishReason", ""))
        chunks = [p["text"] for p in cand["content"]["parts"] if "text" in p]
        return "".join(chunks).strip(), finish
    except (KeyError, IndexError, TypeError):
        return "", finish
