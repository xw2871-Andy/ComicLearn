"""Runtime configuration and environment loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env at import time so CLI invocations work out of the box.
load_dotenv()

# Nano Banana Pro == Gemini 3 Pro Image Preview.
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-3-pro-image"
# Default Gemini text/vision model for lesson, storyboard, and QA when the
# text provider is 'gemini'.
DEFAULT_GEMINI_TEXT_MODEL = "gemini-3.5-flash"


@dataclass(frozen=True)
class Settings:
    # Text/reasoning provider: "anthropic" | "gemini" | "auto"
    text_provider: str
    anthropic_api_key: str | None
    reasoning_model: str
    visual_model: str
    gemini_api_key: str | None
    gemini_text_model: str
    gemini_image_model: str
    gemini_image_resolution: str
    qa_score_threshold: int
    image_backend: str
    mathpix_app_id: str | None
    mathpix_app_key: str | None
    openai_api_key: str | None
    replicate_api_token: str | None
    default_output_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            text_provider=os.getenv("TEXT_PROVIDER", "auto").lower(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            reasoning_model=os.getenv("C2C_REASONING_MODEL", "claude-opus-4-8"),
            visual_model=os.getenv("C2C_VISUAL_MODEL", "claude-opus-4-8"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_text_model=os.getenv(
                "GEMINI_TEXT_MODEL", DEFAULT_GEMINI_TEXT_MODEL
            ),
            gemini_image_model=os.getenv(
                "GEMINI_IMAGE_MODEL", DEFAULT_GEMINI_IMAGE_MODEL
            ),
            gemini_image_resolution=os.getenv("GEMINI_IMAGE_RESOLUTION", "2K"),
            qa_score_threshold=int(os.getenv("C2C_QA_SCORE_THRESHOLD", "80")),
            image_backend=os.getenv("IMAGE_BACKEND", "gemini").lower(),
            mathpix_app_id=os.getenv("MATHPIX_APP_ID"),
            mathpix_app_key=os.getenv("MATHPIX_APP_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            replicate_api_token=os.getenv("REPLICATE_API_TOKEN"),
            default_output_dir=Path(
                os.getenv("C2C_OUTPUT_DIR", "outputs")
            ).expanduser(),
        )

    # ----- provider helpers ------------------------------------------------ #

    def resolve_text_provider(self, requested: str | None = None) -> str:
        """Pick the text provider, honoring an explicit request, then env,
        then whichever API key is actually configured."""

        choice = (requested or self.text_provider or "auto").lower()
        if choice in {"anthropic", "claude"}:
            return "anthropic"
        if choice == "gemini":
            return "gemini"
        # auto: prefer Anthropic when its key exists, else Gemini.
        if self.anthropic_api_key:
            return "anthropic"
        if self.gemini_api_key:
            return "gemini"
        return "anthropic"  # will raise a clear error on first use

    def has_mathpix(self) -> bool:
        return bool(self.mathpix_app_id and self.mathpix_app_key)

    def require_anthropic(self) -> str:
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your environment or "
                ".env file, or switch the text provider to 'gemini'."
            )
        return self.anthropic_api_key

    def require_gemini(self) -> str:
        if not self.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your environment or .env "
                "file. Gemini is required for Nano Banana Pro image generation."
            )
        return self.gemini_api_key


SETTINGS = Settings.from_env()
