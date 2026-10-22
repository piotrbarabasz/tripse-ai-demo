import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.sharing import token_hash


def now():
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id TEXT PRIMARY KEY,
                    request_text TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('queued', 'running', 'completed', 'failed')
                    ),
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS trips_queue ON trips(status, created_at)"
            )
            connection.execute("""
                CREATE TABLE IF NOT EXISTS waha_messages (
                    session TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    trip_id TEXT NOT NULL REFERENCES trips(trip_id),
                    ack_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (ack_status IN ('pending', 'sending', 'sent')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    retry_after REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (session, message_id)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS trip_viewers (
                    token_hash TEXT PRIMARY KEY,
                    trip_id TEXT NOT NULL UNIQUE REFERENCES trips(trip_id),
                    expires_at REAL NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS waha_results (
                    trip_id TEXT PRIMARY KEY REFERENCES trips(trip_id),
                    session TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'sending', 'sent')),
                    retry_after REAL NOT NULL DEFAULT 0
                )
            """)

    def get_viewer(self, token):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT trips.result_json FROM trip_viewers JOIN trips USING (trip_id) "
                "WHERE token_hash = ? AND expires_at > ? AND trips.status = 'completed'",
                (token_hash(token), time.time()),
            ).fetchone()
        return json.loads(row["result_json"]) if row else None

    def claim_result(self):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT r.* FROM waha_results r WHERE r.status = 'pending' AND r.retry_after <= ? "
                "AND EXISTS (SELECT 1 FROM waha_messages m WHERE m.trip_id = r.trip_id "
                "AND m.ack_status = 'sent') ORDER BY r.retry_after, r.rowid LIMIT 1", (time.time(),),
            ).fetchone()
            if row is None:
                return None
            connection.execute("UPDATE waha_results SET status = 'sending' WHERE trip_id = ?",
                               (row["trip_id"],))
            return dict(row)

    def finish_result(self, notification, *, sent):
        with self.connect() as connection:
            connection.execute(
                "UPDATE waha_results SET status = ?, retry_after = ? WHERE trip_id = ?",
                ("sent" if sent else "pending", time.time() + 30, notification["trip_id"]),
            )

    def create_waha_trip(self, session, message_id, sender, text):
        # Deduplication, job and pending acknowledgement commit together.
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT trip_id FROM waha_messages WHERE session = ? AND message_id = ?",
                (session, message_id),
            ).fetchone()
            if existing:
                return existing["trip_id"], False
            trip_id, timestamp = str(uuid4()), now()
            connection.execute(
                "INSERT INTO trips VALUES (?, ?, 'queued', NULL, NULL, ?, ?)",
                (trip_id, text, timestamp, timestamp),
            )
            connection.execute(
                "INSERT INTO waha_messages (session, message_id, sender, trip_id) VALUES (?, ?, ?, ?)",
                (session, message_id, sender, trip_id),
            )
            return trip_id, True

    def claim_ack(self):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM waha_messages WHERE ack_status = 'pending' AND retry_after <= ? "
                "ORDER BY retry_after, rowid LIMIT 1", (time.time(),),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE waha_messages SET ack_status = 'sending', attempts = attempts + 1 "
                "WHERE session = ? AND message_id = ?", (row["session"], row["message_id"]),
            )
            return dict(row)

    def finish_ack(self, ack, *, sent):
        with self.connect() as connection:
            connection.execute(
                "UPDATE waha_messages SET ack_status = ?, retry_after = ? "
                "WHERE session = ? AND message_id = ?",
                ("sent" if sent else "pending", time.time() + 30,
                 ack["session"], ack["message_id"]),
            )

    def create_trip(self, request_text):
        trip_id = str(uuid4())
        timestamp = now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO trips VALUES (?, ?, 'queued', NULL, NULL, ?, ?)",
                (trip_id, request_text, timestamp, timestamp),
            )
        return trip_id

    def get_trip(self, trip_id):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM trips WHERE trip_id = ?", (trip_id,)
            ).fetchone()
        if row is None:
            return None
        trip = dict(row)
        trip["result"] = json.loads(trip.pop("result_json")) if row["result_json"] else None
        return trip

    def claim_next(self):
        # Claim and state transition are atomic, even while the API writes jobs.
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT trip_id, request_text FROM trips "
                "WHERE status = 'queued' ORDER BY created_at, trip_id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE trips SET status = 'running', updated_at = ? WHERE trip_id = ?",
                (now(), row["trip_id"]),
            )
            return dict(row)

    def finish(self, trip_id, *, result=None, error=None, viewer_token=None,
               viewer_expires_at=None, notification=None):
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE trips SET status = ?, result_json = ?, error = ?, updated_at = ? "
                "WHERE trip_id = ? AND status = 'running'",
                (
                    "failed" if error is not None else "completed",
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    error,
                    now(),
                    trip_id,
                ),
            )
            if cursor.rowcount != 1:
                return
            if viewer_token is not None:
                connection.execute(
                    "INSERT INTO trip_viewers VALUES (?, ?, ?)",
                    (token_hash(viewer_token), trip_id, viewer_expires_at),
                )
            if notification:
                connection.execute(
                    "INSERT OR IGNORE INTO waha_results (trip_id, session, sender, text) "
                    "SELECT trip_id, session, sender, ? FROM waha_messages WHERE trip_id = ?",
                    (notification, trip_id),
                )

    def recover_interrupted(self):
        # Only one worker process is supported. Mock generation is safe to retry.
        with self.connect() as connection:
            connection.execute(
                "UPDATE trips SET status = 'queued', updated_at = ? WHERE status = 'running'",
                (now(),),
            )
            connection.execute(
                "UPDATE waha_messages SET ack_status = 'pending' WHERE ack_status = 'sending'"
            )
            connection.execute("UPDATE waha_results SET status = 'pending' WHERE status = 'sending'")

    def check(self):
        with self.connect() as connection:
            connection.execute("SELECT trip_id FROM trips LIMIT 1").fetchall()
