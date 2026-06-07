"""SQLite-backed data layer for the AI Comic Book studio.

Tables
------
- ``users``     : registered accounts (email, password hash, created_at)
- ``sessions``  : long-lived session tokens (token, user_id, created_at, expires_at)
- ``projects``  : top-level user projects (id, user_id, name, created_at, updated_at)
- ``runs``      : individual generation runs scoped to a project
- ``events``    : append-only progress events per run (for SSE replay)

No ORM. Stdlib ``sqlite3`` only. Thread-safe via per-call connections.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(os.environ.get("C2C_DB_PATH", "outputs/studio.db")).expanduser()
_INIT_LOCK = threading.Lock()
_INITIALIZED = False


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    pwd_salt      TEXT NOT NULL,
    pwd_hash      TEXT NOT NULL,
    created_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token         TEXT PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    INTEGER NOT NULL,
    expires_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id            TEXT PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    grade_level   TEXT NOT NULL,
    cast_json     TEXT NOT NULL DEFAULT '[]',
    setting_hint  TEXT,
    created_at    INTEGER NOT NULL,
    updated_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    grade_level   TEXT NOT NULL,
    source_kind   TEXT NOT NULL,          -- topic | markdown | pdf
    source_text   TEXT,                   -- markdown/topic preview
    backend       TEXT NOT NULL,          -- svg | gemini
    run_qa        INTEGER NOT NULL DEFAULT 1,
    status        TEXT NOT NULL,          -- queued | running | done | error
    error         TEXT,
    run_dir       TEXT,                   -- absolute path to outputs/runs/<ts>_<slug>
    pdf_path      TEXT,
    created_at    INTEGER NOT NULL,
    finished_at   INTEGER
);

CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    kind          TEXT NOT NULL,          -- info | step | warn | error | done | panel
    payload_json  TEXT NOT NULL,
    created_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id, updated_at DESC);
"""


def now_ts() -> int:
    return int(time.time())


def new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:24]
    return f"{prefix}{base}" if prefix else base


def init_db() -> None:
    """Create the schema (idempotent). Safe to call many times."""

    global _INITIALIZED
    with _INIT_LOCK:
        if _INITIALIZED:
            return
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript(SCHEMA)
            conn.commit()
        _INITIALIZED = True


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Yield a sqlite3 connection with row_factory=Row and FK enforcement on."""

    init_db()
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


# ----- Users / sessions ------------------------------------------------------ #


def create_user(email: str, display_name: str, pwd_salt: str, pwd_hash: str) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO users(email, display_name, pwd_salt, pwd_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (email.lower(), display_name, pwd_salt, pwd_hash, now_ts()),
        )
        return int(cur.lastrowid)


def get_user_by_email(email: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        return dict(row) if row else None


def get_user(user_id: int) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_session(user_id: int, ttl_seconds: int = 60 * 60 * 24 * 30) -> str:
    token = new_id("sess_")
    now = now_ts()
    with connect() as c:
        c.execute(
            "INSERT INTO sessions(token, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (token, user_id, now, now + ttl_seconds),
        )
    return token


def get_session(token: str) -> dict | None:
    if not token:
        return None
    with connect() as c:
        row = c.execute(
            "SELECT * FROM sessions WHERE token = ? AND expires_at > ?",
            (token, now_ts()),
        ).fetchone()
        return dict(row) if row else None


def delete_session(token: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM sessions WHERE token = ?", (token,))


# ----- Projects -------------------------------------------------------------- #


def create_project(
    user_id: int,
    name: str,
    grade_level: str,
    cast: list[str],
    setting_hint: str | None,
) -> dict:
    pid = new_id("proj_")
    now = now_ts()
    with connect() as c:
        c.execute(
            "INSERT INTO projects(id, user_id, name, grade_level, cast_json, "
            "setting_hint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, user_id, name, grade_level, json.dumps(cast), setting_hint, now, now),
        )
    return get_project(pid, user_id)  # type: ignore[return-value]


def get_project(project_id: str, user_id: int) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["cast"] = json.loads(d.pop("cast_json") or "[]")
        return d


def list_projects(user_id: int) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["cast"] = json.loads(d.pop("cast_json") or "[]")
            # also include run counts
            d["run_count"] = c.execute(
                "SELECT COUNT(*) FROM runs WHERE project_id = ?", (d["id"],)
            ).fetchone()[0]
            out.append(d)
        return out


def update_project(project_id: str, user_id: int, **fields: Any) -> dict | None:
    if not fields:
        return get_project(project_id, user_id)
    cols = []
    vals: list[Any] = []
    for k, v in fields.items():
        if k == "cast":
            cols.append("cast_json = ?")
            vals.append(json.dumps(v))
        elif k in {"name", "grade_level", "setting_hint"}:
            cols.append(f"{k} = ?")
            vals.append(v)
    if not cols:
        return get_project(project_id, user_id)
    cols.append("updated_at = ?")
    vals.append(now_ts())
    vals.extend([project_id, user_id])
    with connect() as c:
        c.execute(
            f"UPDATE projects SET {', '.join(cols)} WHERE id = ? AND user_id = ?",
            vals,
        )
    return get_project(project_id, user_id)


def delete_project(project_id: str, user_id: int) -> bool:
    with connect() as c:
        cur = c.execute(
            "DELETE FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id),
        )
        return cur.rowcount > 0


# ----- Runs ------------------------------------------------------------------ #


def create_run(
    *,
    project_id: str,
    user_id: int,
    title: str,
    grade_level: str,
    source_kind: str,
    source_text: str | None,
    backend: str,
    run_qa: bool,
) -> dict:
    rid = new_id("run_")
    with connect() as c:
        c.execute(
            "INSERT INTO runs(id, project_id, user_id, title, grade_level, "
            "source_kind, source_text, backend, run_qa, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)",
            (
                rid, project_id, user_id, title, grade_level,
                source_kind, source_text, backend, 1 if run_qa else 0, now_ts(),
            ),
        )
        c.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (now_ts(), project_id),
        )
    return get_run(rid, user_id)  # type: ignore[return-value]


def update_run(run_id: str, **fields: Any) -> None:
    if not fields:
        return
    cols = []
    vals: list[Any] = []
    for k, v in fields.items():
        if k in {"status", "error", "run_dir", "pdf_path", "finished_at"}:
            cols.append(f"{k} = ?")
            vals.append(v)
    if not cols:
        return
    vals.append(run_id)
    with connect() as c:
        c.execute(f"UPDATE runs SET {', '.join(cols)} WHERE id = ?", vals)


def get_run(run_id: str, user_id: int | None = None) -> dict | None:
    with connect() as c:
        if user_id is None:
            row = c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        else:
            row = c.execute(
                "SELECT * FROM runs WHERE id = ? AND user_id = ?", (run_id, user_id)
            ).fetchone()
        return dict(row) if row else None


def list_runs(project_id: str, user_id: int, limit: int = 50) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM runs WHERE project_id = ? AND user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (project_id, user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ----- Events ---------------------------------------------------------------- #


def append_event(run_id: str, seq: int, kind: str, payload: dict) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO events(run_id, seq, kind, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, seq, kind, json.dumps(payload), now_ts()),
        )


def list_events(run_id: str, after_seq: int = 0) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE run_id = ? AND seq > ? ORDER BY seq ASC",
            (run_id, after_seq),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.pop("payload_json"))
            out.append(d)
        return out
