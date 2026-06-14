"""Text-provider factory.

The pipeline's text steps (lesson plan, worksheet, storyboard, QA vision
review) can run on either Anthropic Claude or Google Gemini. Image
generation always runs on Gemini (Nano Banana Pro) regardless of this
choice.

Both clients expose the same four methods::

    complete(system=..., user=..., ...) -> str
    complete_json(system=..., user=..., ...) -> dict
    complete_with_image(system=..., user_text=..., image_bytes=..., ...) -> str
    complete_json_with_image(...) -> dict
"""

from __future__ import annotations

from typing import Protocol, Any

from .config import SETTINGS


class TextClient(Protocol):
    def complete(self, **kwargs: Any) -> str: ...
    def complete_json(self, **kwargs: Any) -> dict: ...
    def complete_with_image(self, **kwargs: Any) -> str: ...
    def complete_json_with_image(self, **kwargs: Any) -> dict: ...


def get_text_client(provider: str | None = None) -> TextClient:
    """Return a ready-to-use text client for ``provider``.

    ``provider`` may be "anthropic", "gemini", "auto", or None (= env/auto).
    """

    resolved = SETTINGS.resolve_text_provider(provider)
    if resolved == "gemini":
        from .gemini_client import GeminiTextClient

        return GeminiTextClient()
    from .claude_client import ClaudeClient

    return ClaudeClient()
