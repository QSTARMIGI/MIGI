from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TreLogic(str, Enum):
    ALLOW = "+1"
    HOLD = "0"
    DENY = "-1"


class SourceClass(str, Enum):
    ORIGINAL = "original"
    OBSERVED = "observed"
    DERIVED = "derived"
    SIMULATED = "simulated"
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    EXECUTED = "executed"


class Serializable:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MIGIIntent(Serializable):
    intent_id: str
    created_at: str
    actor_id: str
    action: str
    target_ref: str
    consent_scope: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MIGIArtifact(Serializable):
    artifact_id: str
    observed_at: str
    path: str
    sha256: str
    size_bytes: int
    media_type: str
    source_class: str = SourceClass.OBSERVED.value


@dataclass(frozen=True)
class MIGIAuthority(Serializable):
    authority_id: str
    decided_at: str
    intent_id: str
    tre_logic: str
    reason_code: str
    consent_scope: str


@dataclass(frozen=True)
class MIGIExecution(Serializable):
    execution_id: str
    started_at: str
    completed_at: str
    intent_id: str
    authority_id: str
    executor: str
    operation: str
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MIGIReceipt(Serializable):
    schema_version: str
    receipt_id: str
    issued_at: str
    event_id: str
    source_class: str
    intent_ref: str
    output_ref: str
    previous_receipt_ref: str
    authority: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MIGIMemory(Serializable):
    memory_id: str
    created_at: str
    subject_ref: str
    receipt_id: str
    kind: str
    summary: str
    facts: dict[str, Any] = field(default_factory=dict)
