"""Pluggable image backends.

The default ``svg`` backend lives in :mod:`curriculum_to_comic.illustrator`.
This sub-package holds alternative backends that hit external image-gen APIs.
"""

from .gemini_nano_banana import GeminiNanoBananaBackend

__all__ = ["GeminiNanoBananaBackend"]
