"""Thin wrapper around the Anthropic SDK with retries and JSON helpers."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import SETTINGS


class ClaudeClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._client = Anthropic(api_key=api_key or SETTINGS.require_anthropic())

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
        """Single-turn completion. Returns the text content."""

        resp = self._client.messages.create(
            model=model or SETTINGS.reasoning_model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user}],
        )
        parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts).strip()

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
        """Multimodal completion: one image + one text block.

        Used by the QA subagent to review a generated panel against the
        storyboard scene description.
        """

        b64 = base64.b64encode(image_bytes).decode("ascii")
        resp = self._client.messages.create(
            model=model or SETTINGS.reasoning_model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                }
            ],
        )
        parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts).strip()

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
        return _parse_json_lenient(raw)

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """Like :meth:`complete` but parses the response as JSON.

        Tolerates ```json``` fences and stray prose by extracting the first
        balanced JSON object in the response.
        """

        raw = self.complete(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return _parse_json_lenient(raw)


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parse_json_lenient(raw: str) -> dict[str, Any]:
    """Extract a JSON object from a possibly-wrapped LLM response."""

    raw = raw.strip()
    # 1. Direct parse.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Fenced code block.
    m = _FENCE_RE.search(raw)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3. First balanced { ... } substring.
    start = raw.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = raw[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ValueError(
        "Claude response was not valid JSON. First 400 chars:\n" + raw[:400]
    )
