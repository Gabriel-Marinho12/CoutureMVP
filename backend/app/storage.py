"""Persistence: SQLite for records, the filesystem for original files and previews.

Originals are stored by hash and are never served; only downscaled,
watermarked derivatives leave the server.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS designs (
    id            TEXT PRIMARY KEY,
    sha256        TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    designer      TEXT NOT NULL,
    filename      TEXT NOT NULL,
    content_type  TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    has_preview   INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL,
    signature     TEXT,
    slot          INTEGER,
    error         TEXT,
    created_at    TEXT NOT NULL,
    registered_at TEXT
);
CREATE TABLE IF NOT EXISTS certificates (
    id           TEXT PRIMARY KEY,
    design_id    TEXT NOT NULL REFERENCES designs(id),
    owner        TEXT NOT NULL,
    status       TEXT NOT NULL,
    signature    TEXT,
    asset_id     TEXT,
    error        TEXT,
    created_at   TEXT NOT NULL,
    confirmed_at TEXT
);
CREATE INDEX IF NOT EXISTS certificates_design ON certificates(design_id);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

# Lifecycle shared by designs and certificates.
PENDING, CONFIRMED, FAILED, UNCONFIRMED = "pending", "confirmed", "failed", "unconfirmed"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass
class Design:
    id: str
    sha256: str
    title: str
    designer: str
    filename: str
    content_type: str
    size_bytes: int
    has_preview: bool
    status: str
    signature: str | None
    slot: int | None
    error: str | None
    created_at: str
    registered_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Certificate:
    id: str
    design_id: str
    owner: str
    status: str
    signature: str | None
    asset_id: str | None
    error: str | None
    created_at: str
    confirmed_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.originals = data_dir / "originals"
        self.previews = data_dir / "previews"
        self.tmp = data_dir / "tmp"
        for path in (self.originals, self.previews, self.tmp):
            path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(data_dir / "couture.db", check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            self._db.execute("COMMIT")

    def _one(self, sql: str, *args: Any) -> sqlite3.Row | None:
        with self._lock:
            return self._db.execute(sql, args).fetchone()

    def _all(self, sql: str, *args: Any) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # ---- files -------------------------------------------------------------

    def original_path(self, sha256: str) -> Path:
        return self.originals / sha256

    def preview_path(self, design_id: str) -> Path:
        return self.previews / f"{design_id}.webp"

    # ---- designs -----------------------------------------------------------

    def claim_design(self, *, sha256: str, title: str, designer: str, filename: str,
                     content_type: str, size_bytes: int) -> tuple[Design, bool]:
        """Create a pending design for this hash, or return the existing one.

        The boolean is True when the caller now owns registration: a new
        record, or a previously failed one reset to pending.
        """
        with self._tx() as db:
            row = db.execute("SELECT * FROM designs WHERE sha256 = ?", (sha256,)).fetchone()
            if row is None:
                design_id = new_id()
                db.execute(
                    "INSERT INTO designs (id, sha256, title, designer, filename, content_type, size_bytes,"
                    " status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (design_id, sha256, title, designer, filename, content_type, size_bytes, PENDING, now()),
                )
            elif row["status"] == FAILED:
                design_id = row["id"]
                db.execute(
                    "UPDATE designs SET title = ?, designer = ?, filename = ?, status = ?, error = NULL,"
                    " signature = NULL WHERE id = ?",
                    (title, designer, filename, PENDING, design_id),
                )
            else:
                return _design(row), False
            return _design(db.execute("SELECT * FROM designs WHERE id = ?", (design_id,)).fetchone()), True

    def update_design(self, design_id: str, **fields: Any) -> Design:
        if fields.get("status") == CONFIRMED:
            fields.setdefault("registered_at", now())
        columns = ", ".join(f"{name} = ?" for name in fields)
        with self._tx() as db:
            db.execute(f"UPDATE designs SET {columns} WHERE id = ?", (*fields.values(), design_id))
            return _design(db.execute("SELECT * FROM designs WHERE id = ?", (design_id,)).fetchone())

    def get_design(self, design_id: str) -> Design | None:
        row = self._one("SELECT * FROM designs WHERE id = ?", design_id)
        return _design(row) if row else None

    def design_by_hash(self, sha256: str) -> Design | None:
        row = self._one("SELECT * FROM designs WHERE sha256 = ?", sha256)
        return _design(row) if row else None

    def list_designs(self, *, status: str | None = None, limit: int = 50) -> list[Design]:
        if status:
            rows = self._all("SELECT * FROM designs WHERE status = ? ORDER BY created_at DESC LIMIT ?", status, limit)
        else:
            rows = self._all("SELECT * FROM designs ORDER BY created_at DESC LIMIT ?", limit)
        return [_design(row) for row in rows]

    def designs_in(self, *statuses: str) -> list[Design]:
        marks = ", ".join("?" for _ in statuses)
        return [_design(row) for row in self._all(f"SELECT * FROM designs WHERE status IN ({marks})", *statuses)]

    # ---- certificates ------------------------------------------------------

    def create_certificate(self, design_id: str, owner: str) -> Certificate:
        cert_id = new_id()
        with self._tx() as db:
            db.execute(
                "INSERT INTO certificates (id, design_id, owner, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (cert_id, design_id, owner, PENDING, now()),
            )
            return _certificate(db.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone())

    def update_certificate(self, cert_id: str, **fields: Any) -> Certificate:
        if fields.get("status") == CONFIRMED:
            fields.setdefault("confirmed_at", now())
        columns = ", ".join(f"{name} = ?" for name in fields)
        with self._tx() as db:
            db.execute(f"UPDATE certificates SET {columns} WHERE id = ?", (*fields.values(), cert_id))
            return _certificate(db.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone())

    def get_certificate(self, cert_id: str) -> Certificate | None:
        row = self._one("SELECT * FROM certificates WHERE id = ?", cert_id)
        return _certificate(row) if row else None

    def certificates_for(self, design_id: str) -> list[Certificate]:
        rows = self._all("SELECT * FROM certificates WHERE design_id = ? ORDER BY created_at DESC", design_id)
        return [_certificate(row) for row in rows]

    def certificates_in(self, *statuses: str) -> list[Certificate]:
        marks = ", ".join("?" for _ in statuses)
        return [_certificate(r) for r in self._all(f"SELECT * FROM certificates WHERE status IN ({marks})", *statuses)]

    # ---- key/value ---------------------------------------------------------

    def get_value(self, key: str) -> str | None:
        row = self._one("SELECT value FROM kv WHERE key = ?", key)
        return row["value"] if row else None

    def set_value(self, key: str, value: str) -> None:
        with self._tx() as db:
            db.execute("INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                       (key, value))


def _design(row: sqlite3.Row) -> Design:
    data = dict(row)
    data["has_preview"] = bool(data["has_preview"])
    return Design(**data)


def _certificate(row: sqlite3.Row) -> Certificate:
    return Certificate(**dict(row))
