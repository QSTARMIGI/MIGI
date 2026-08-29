from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .canonical import chained_hash
from .models import MIGIReceipt


class GenesisStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @contextmanager
    def _session(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS objects (
                    kind TEXT NOT NULL,
                    object_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_objects_kind_created
                ON objects(kind, created_at);

                CREATE TABLE IF NOT EXISTS receipt_chain (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id TEXT NOT NULL UNIQUE,
                    receipt_hash TEXT NOT NULL UNIQUE,
                    previous_receipt_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def put(self, kind: str, object_id: str, created_at: str, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._session() as conn:
            conn.execute(
                "INSERT INTO objects(kind, object_id, created_at, payload_json) VALUES (?, ?, ?, ?)",
                (kind, object_id, created_at, encoded),
            )

    def get(self, object_id: str) -> dict[str, Any] | None:
        with self._session() as conn:
            row = conn.execute(
                "SELECT kind, object_id, created_at, payload_json FROM objects WHERE object_id = ?",
                (object_id,),
            ).fetchone()
        if row is None:
            return None
        return {"kind": row["kind"], **json.loads(row["payload_json"])}

    def list_kind(self, kind: str) -> list[dict[str, Any]]:
        with self._session() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM objects WHERE kind = ? ORDER BY created_at, object_id",
                (kind,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def latest_receipt_hash(self) -> str:
        with self._session() as conn:
            row = conn.execute(
                "SELECT receipt_hash FROM receipt_chain ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        return "" if row is None else str(row["receipt_hash"])

    def append_receipt(self, receipt: MIGIReceipt) -> str:
        payload = receipt.to_dict()
        previous = self.latest_receipt_hash()
        if payload["previous_receipt_ref"] != previous:
            raise ValueError("Receipt previous_receipt_ref does not match current chain head")
        receipt_hash = chained_hash(previous, payload)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._session() as conn:
            conn.execute(
                """
                INSERT INTO receipt_chain(receipt_id, receipt_hash, previous_receipt_hash, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (receipt.receipt_id, receipt_hash, previous, encoded),
            )
        return receipt_hash

    def receipts(self) -> list[dict[str, Any]]:
        with self._session() as conn:
            rows = conn.execute(
                """
                SELECT sequence, receipt_id, receipt_hash, previous_receipt_hash, payload_json
                FROM receipt_chain ORDER BY sequence
                """
            ).fetchall()
        return [
            {
                "sequence": row["sequence"],
                "receipt_hash": row["receipt_hash"],
                "previous_receipt_hash": row["previous_receipt_hash"],
                **json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def verify_chain(self) -> dict[str, Any]:
        previous = ""
        checked = 0
        for item in self.receipts():
            payload = {
                key: value
                for key, value in item.items()
                if key not in {"sequence", "receipt_hash", "previous_receipt_hash"}
            }
            if item["previous_receipt_hash"] != previous:
                return {"valid": False, "checked": checked, "reason": "stored_previous_mismatch"}
            if payload["previous_receipt_ref"] != previous:
                return {"valid": False, "checked": checked, "reason": "payload_previous_mismatch"}
            expected = chained_hash(previous, payload)
            if expected != item["receipt_hash"]:
                return {"valid": False, "checked": checked, "reason": "receipt_hash_mismatch"}
            previous = item["receipt_hash"]
            checked += 1
        return {"valid": True, "checked": checked, "head": previous}
