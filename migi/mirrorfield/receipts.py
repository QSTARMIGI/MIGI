"""Deterministic, tamper-evident receipt helpers for Mirrorfield prototype events.

These hashes detect changes to the serialized record; they do not prove the
physical truth of a sensor observation and are not digital signatures.
"""
from __future__ import annotations

from typing import Any

from migi.canonical import canonical_json_bytes, sha256_hex

RECEIPT_SCHEMA = "mirrorfield-receipt.v0"


def make_receipt(*, event_id: str, source_class: str, input_refs: list[str],
                 output_ref: str, created_at_ns: int, previous_hash: str = "") -> dict[str, Any]:
    if not event_id or not output_ref:
        raise ValueError("event_id and output_ref are required")
    if created_at_ns < 0:
        raise ValueError("created_at_ns must be non-negative")
    if source_class not in {"original", "observed", "derived", "simulated", "proposed"}:
        raise ValueError("unsupported source_class")
    if any(not isinstance(ref, str) or not ref for ref in input_refs):
        raise ValueError("input_refs must contain non-empty strings")
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "event_id": event_id,
        "source_class": source_class,
        "input_refs": list(input_refs),
        "output_ref": output_ref,
        "created_at_ns": created_at_ns,
        "previous_hash": previous_hash,
    }
    payload["record_hash"] = sha256_hex(canonical_json_bytes(payload))
    return payload


def verify_receipt(receipt: dict[str, Any]) -> bool:
    if not isinstance(receipt, dict) or receipt.get("schema_version") != RECEIPT_SCHEMA:
        return False
    claimed = receipt.get("record_hash")
    if not isinstance(claimed, str):
        return False
    payload = {key: value for key, value in receipt.items() if key != "record_hash"}
    try:
        return sha256_hex(canonical_json_bytes(payload)) == claimed
    except (TypeError, ValueError):
        return False
