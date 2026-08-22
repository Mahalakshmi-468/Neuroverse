"""
Lightweight SQLite persistence for NeuroVerse story sessions.

No ORM — this app has one table and simple access patterns, so plain
sqlite3 keeps things easy to read and dependency-free.

v0.3 adds traits / inventory / achievements / puzzle-progress columns,
migrated in automatically for existing databases via ALTER TABLE so
upgrading never loses a saved mission.
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    player     TEXT NOT NULL,
    idea       TEXT NOT NULL,
    world      TEXT NOT NULL,
    companion  TEXT NOT NULL,
    artifact   TEXT NOT NULL,
    chapter    INTEGER NOT NULL DEFAULT 1,
    score      INTEGER NOT NULL DEFAULT 0,
    health     INTEGER NOT NULL DEFAULT 100,
    finished   INTEGER NOT NULL DEFAULT 0,
    story      TEXT NOT NULL,
    mission    TEXT NOT NULL,
    choices    TEXT NOT NULL,
    history    TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'offline',
    traits         TEXT NOT NULL DEFAULT '{"bravery":0,"curiosity":0,"kindness":0}',
    inventory      TEXT NOT NULL DEFAULT '[]',
    achievements   TEXT NOT NULL DEFAULT '[]',
    puzzle_correct INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# Columns added after the original v0.1/v0.2 schema. Applied defensively
# so existing databases upgrade in place without losing saved missions.
MIGRATION_COLUMNS = [
    ("traits", "TEXT NOT NULL DEFAULT '{\"bravery\":0,\"curiosity\":0,\"kindness\":0}'"),
    ("inventory", "TEXT NOT NULL DEFAULT '[]'"),
    ("achievements", "TEXT NOT NULL DEFAULT '[]'"),
    ("puzzle_correct", "INTEGER NOT NULL DEFAULT 0"),
]


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
        for name, ddl in MIGRATION_COLUMNS:
            if name not in existing:
                conn.execute(f"ALTER TABLE sessions ADD COLUMN {name} {ddl}")


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_session(state: dict) -> dict:
    session_id = str(uuid.uuid4())
    now = _now()
    row = {
        "session_id": session_id,
        "player": state["player"],
        "idea": state["idea"],
        "world": state["world"],
        "companion": state["companion"],
        "artifact": state["artifact"],
        "chapter": state["chapter"],
        "score": state["score"],
        "health": state["health"],
        "finished": int(state["finished"]),
        "story": state["story"],
        "mission": state["mission"],
        "choices": json.dumps(state["choices"]),
        "history": json.dumps(state["history"]),
        "source": state["source"],
        "traits": json.dumps(state.get("traits", {"bravery": 0, "curiosity": 0, "kindness": 0})),
        "inventory": json.dumps(state.get("inventory", [])),
        "achievements": json.dumps(state.get("achievements", [])),
        "puzzle_correct": state.get("puzzle_correct", 0),
        "created_at": now,
        "updated_at": now,
    }
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions
               (session_id, player, idea, world, companion, artifact, chapter,
                score, health, finished, story, mission, choices, history,
                source, traits, inventory, achievements, puzzle_correct,
                created_at, updated_at)
               VALUES (:session_id, :player, :idea, :world, :companion, :artifact,
                       :chapter, :score, :health, :finished, :story, :mission,
                       :choices, :history, :source, :traits, :inventory,
                       :achievements, :puzzle_correct, :created_at, :updated_at)""",
            row,
        )
    return load_session(session_id)


def update_session(session_id: str, state: dict) -> dict:
    with get_conn() as conn:
        conn.execute(
            """UPDATE sessions SET
                 chapter=:chapter, score=:score, health=:health, finished=:finished,
                 story=:story, mission=:mission, choices=:choices, history=:history,
                 source=:source, traits=:traits, inventory=:inventory,
                 achievements=:achievements, puzzle_correct=:puzzle_correct,
                 updated_at=:updated_at
               WHERE session_id=:session_id""",
            {
                "session_id": session_id,
                "chapter": state["chapter"],
                "score": state["score"],
                "health": state["health"],
                "finished": int(state["finished"]),
                "story": state["story"],
                "mission": state["mission"],
                "choices": json.dumps(state["choices"]),
                "history": json.dumps(state["history"]),
                "source": state["source"],
                "traits": json.dumps(state.get("traits", {"bravery": 0, "curiosity": 0, "kindness": 0})),
                "inventory": json.dumps(state.get("inventory", [])),
                "achievements": json.dumps(state.get("achievements", [])),
                "puzzle_correct": state.get("puzzle_correct", 0),
                "updated_at": _now(),
            },
        )
    return load_session(session_id)


def _row_to_state(row: sqlite3.Row) -> dict:
    return {
        "session_id": row["session_id"],
        "player": row["player"],
        "idea": row["idea"],
        "world": row["world"],
        "companion": row["companion"],
        "artifact": row["artifact"],
        "chapter": row["chapter"],
        "max_chapters": config.MAX_CHAPTERS,
        "score": row["score"],
        "health": row["health"],
        "finished": bool(row["finished"]),
        "story": row["story"],
        "mission": row["mission"],
        "choices": json.loads(row["choices"]),
        "history": json.loads(row["history"]),
        "source": row["source"],
        "traits": json.loads(row["traits"] or '{"bravery":0,"curiosity":0,"kindness":0}'),
        "inventory": json.loads(row["inventory"] or "[]"),
        "achievements": json.loads(row["achievements"] or "[]"),
        "puzzle_correct": row["puzzle_correct"] or 0,
    }


def load_session(session_id: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row is None:
        raise KeyError(session_id)
    return _row_to_state(row)


def list_sessions() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 50"
        ).fetchall()
    return [
        {
            "session_id": r["session_id"],
            "player": r["player"],
            "world": r["world"],
            "chapter": r["chapter"],
            "score": r["score"],
            "health": r["health"],
            "finished": bool(r["finished"]),
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def delete_session(session_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
