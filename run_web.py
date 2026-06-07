"""Launch the ComicTeach studio web app.

Usage::

    pip install -e ".[web]"     # one-time, installs fastapi + uvicorn
    python run_web.py           # listens on http://127.0.0.1:8000

Environment variables (optional)::

    HOST                 default 127.0.0.1
    PORT                 default 8000
    DEFAULT_OUTPUT_DIR   default ./outputs
    C2C_DB_PATH          default outputs/studio.db
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        import uvicorn  # noqa: WPS433
    except ImportError:
        print(
            "uvicorn is not installed. Install the web extras first:\n"
            "    pip install -e \".[web]\"\n"
            "(or: pip install fastapi uvicorn)",
            file=sys.stderr,
        )
        return 1

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host

    print(f"ComicTeach Studio · http://{display_host}:{port}")
    uvicorn.run("web.app:app", host=host, port=port, reload=False, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
