from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .models import SourceClass
from .util import new_id, utc_now

_EVENT_TYPE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


@dataclass(frozen=True)
class MUEFActor:
    type: str
    id: str


@dataclass(frozen=True)
class MUEFEvent:
    schema_version: str
    event_id: str
    event_type: str
    occurred_at: str
    actor: MUEFActor
    source_class: str
    payload: dict[str, Any] = field(default_factory=dict)
    parent_event_id: str | None = None
    receipt_id: str | None = None

    @classmethod
    def create(
        cls,
        event_type: str,
        *,
        actor_id: str,
        actor_type: str = "service",
        source_class: str = SourceClass.ORIGINAL.value,
        payload: dict[str, Any] | None = None,
    ) -> "MUEFEvent":
        event = cls(
            schema_version="muef.v0",
            event_id=new_id("event"),
            event_type=event_type,
            occurred_at=utc_now(),
            actor=MUEFActor(type=actor_type, id=actor_id),
            source_class=source_class,
            payload=dict(payload or {}),
        )
        event.validate()
        return event

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MUEFEvent":
        actor = value.get("actor") or {}
        event = cls(
            schema_version=str(value.get("schema_version", "")),
            event_id=str(value.get("event_id", "")),
            event_type=str(value.get("event_type", "")),
            occurred_at=str(value.get("occurred_at", "")),
            actor=MUEFActor(type=str(actor.get("type", "")), id=str(actor.get("id", ""))),
            source_class=str(value.get("source_class", "")),
            payload=dict(value.get("payload") or {}),
            parent_event_id=value.get("parent_event_id"),
            receipt_id=value.get("receipt_id"),
        )
        event.validate()
        return event

    def validate(self) -> None:
        if self.schema_version != "muef.v0":
            raise ValueError("MUEF schema_version must be muef.v0")
        if not self.event_id:
            raise ValueError("MUEF event_id is required")
        if not _EVENT_TYPE.fullmatch(self.event_type):
            raise ValueError("MUEF event_type must be lowercase and namespaced")
        if self.actor.type not in {"user", "agent", "service", "device", "organization"}:
            raise ValueError("Unsupported MUEF actor type")
        if not self.actor.id:
            raise ValueError("MUEF actor id is required")
        if self.source_class not in {item.value for item in SourceClass}:
            raise ValueError("Unsupported MUEF source_class")
        if not isinstance(self.payload, dict):
            raise ValueError("MUEF payload must be an object")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if self.parent_event_id is None:
            value.pop("parent_event_id")
        if self.receipt_id is None:
            value.pop("receipt_id")
        return value
