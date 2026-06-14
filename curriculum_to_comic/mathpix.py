"""Mathpix PDF OCR client (stdlib-only, no extra dependencies).

Mathpix converts textbook PDFs — including equations — into Markdown with
proper LaTeX, which is dramatically better input for math lessons than plain
text extraction. Used automatically by the PDF extractor whenever
``MATHPIX_APP_ID`` / ``MATHPIX_APP_KEY`` are configured; otherwise the
pipeline falls back to local pdfplumber extraction.

API flow (https://docs.mathpix.com):
1. ``POST /v3/pdf`` (multipart) with the file + conversion options.
2. Poll ``GET /v3/pdf/{pdf_id}`` until ``status == "completed"``.
3. ``GET /v3/pdf/{pdf_id}.mmd`` for the Markdown (LaTeX math included).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .config import SETTINGS

_API_ROOT = "https://api.mathpix.com/v3/pdf"


class MathpixError(RuntimeError):
    pass


def mathpix_available() -> bool:
    return SETTINGS.has_mathpix()


def extract_pdf_markdown(
    path: Path,
    *,
    page_range: tuple[int, int] | None = None,
    timeout_s: int = 300,
    poll_interval_s: float = 4.0,
) -> str:
    """OCR a PDF through Mathpix and return Markdown (with LaTeX math)."""

    if not mathpix_available():
        raise MathpixError("MATHPIX_APP_ID / MATHPIX_APP_KEY are not configured.")

    options: dict = {"conversion_formats": {"md": True}}
    if page_range:
        lo, hi = page_range
        options["page_ranges"] = f"{lo}-{hi}"

    pdf_id = _upload(path, options)

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = _get_json(f"{_API_ROOT}/{pdf_id}")
        st = status.get("status")
        if st == "completed":
            return _get_text(f"{_API_ROOT}/{pdf_id}.mmd")
        if st == "error":
            raise MathpixError(
                f"Mathpix conversion failed: {json.dumps(status)[:300]}"
            )
        time.sleep(poll_interval_s)
    raise MathpixError(f"Mathpix conversion timed out after {timeout_s}s.")


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #


def _headers() -> dict[str, str]:
    return {
        "app_id": SETTINGS.mathpix_app_id or "",
        "app_key": SETTINGS.mathpix_app_key or "",
    }


def _upload(path: Path, options: dict) -> str:
    boundary = f"----c2c{uuid.uuid4().hex}"
    file_bytes = path.read_bytes()
    parts: list[bytes] = []

    def field(name: str, value: str) -> None:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )

    field("options_json", json.dumps(options))
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{path.name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(file_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(
        _API_ROOT,
        data=body,
        headers={
            **_headers(),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    data = _send_json(req)
    pdf_id = data.get("pdf_id")
    if not pdf_id:
        raise MathpixError(f"Mathpix upload failed: {json.dumps(data)[:300]}")
    return str(pdf_id)


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=_headers())
    return _send_json(req)


def _get_text(url: str) -> str:
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise MathpixError(f"Mathpix HTTP {exc.code}: {detail[:300]}") from exc


def _send_json(req: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise MathpixError(f"Mathpix HTTP {exc.code}: {detail[:300]}") from exc
