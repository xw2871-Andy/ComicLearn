"""Runtime configuration and environment loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env at import time so CLI invocations work out of the box.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    reasoning_model: str
    visual_model: str
    image_backend: str
    gemini_api_key: str | None
    openai_api_key: str | None
    replicate_api_token: str | None
    default_output_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            reasoning_model=os.getenv("C2C_REASONING_MODEL", "claude-sonnet-4-5"),
            visual_model=os.getenv("C2C_VISUAL_MODEL", "claude-sonnet-4-5"),
            image_backend=os.getenv("IMAGE_BACKEND", "svg").lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            replicate_api_token=os.getenv("REPLICATE_API_TOKEN"),
            default_output_dir=Path(
                os.getenv("C2C_OUTPUT_DIR", "outputs")
            ).expanduser(),
        )

    def require_anthropic(self) -> str:
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your environment or .env file."
            )
        return self.anthropic_api_key


SETTINGS = Settings.from_env()
