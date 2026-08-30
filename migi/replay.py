from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical import canonical_json_bytes, sha256_hex
from .events import MUEFEvent
from .storage import GenesisStore


@dataclass(frozen=True)
class ReplayResult:
    state: dict[str, Any] = field(default_factory=dict)
    applied_events: int = 0
    skipped_events: int = 0
    chain_head: str = ""
    state_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "applied_events": self.applied_events,
            "skipped_events": self.skipped_events,
            "chain_head": self.chain_head,
            "state_hash": self.state_hash,
        }


def replay_verified_state(store: GenesisStore) -> ReplayResult:
    verification = store.verify_chain()
    if not verification.get("valid"):
        raise ValueError(f"Cannot replay invalid receipt chain: {verification.get('reason')}")

    receipts = {
        receipt.get("output_ref"): receipt
        for receipt in store.receipts()
        if receipt.get("source_class") == "executed"
        and receipt.get("authority", {}).get("tre_logic") == "+1"
    }

    state: dict[str, Any] = {}
    applied = 0
    skipped = 0

    for raw_event in store.list_kind("muef_event"):
        event = MUEFEvent.from_dict(raw_event)
        receipt = receipts.get(event.event_id)
        if receipt is None or event.event_type != "migi.state.patch":
            skipped += 1
            continue

        patch = event.payload.get("state_patch")
        if not isinstance(patch, dict):
            skipped += 1
            continue

        for key in sorted(patch):
            if not isinstance(key, str):
                raise ValueError("State patch keys must be strings")
            value = patch[key]
            if value is None:
                state.pop(key, None)
            else:
                state[key] = value
        applied += 1

    state_hash = sha256_hex(canonical_json_bytes(state))
    return ReplayResult(
        state=state,
        applied_events=applied,
        skipped_events=skipped,
        chain_head=str(verification.get("head", "")),
        state_hash=state_hash,
    )
