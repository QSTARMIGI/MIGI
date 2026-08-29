from __future__ import annotations

import hashlib
import json
from typing import Any


def _reject_float(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("Genesis canonical JSON forbids floating-point values in hashed records")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Canonical JSON object keys must be strings")
            _reject_float(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_float(item)


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for Genesis v0.1 records.

    v0.1 intentionally rejects floats so the hash input is stable across runtimes.
    This is a narrow deterministic format, not a claim of full RFC 8785 support.
    """
    _reject_float(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chained_hash(previous_hash: str, payload: Any) -> str:
    material = previous_hash.encode("ascii") + b"\n" + canonical_json_bytes(payload)
    return sha256_hex(material)
