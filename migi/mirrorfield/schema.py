"""Versioned, dependency-free data contracts for Mirrorfield v0.1."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ObservationKind(str, Enum):
    VISUAL = "visual"
    AUDIO = "audio"
    SPATIAL = "spatial"
    EVENT = "event"


class SourceClass(str, Enum):
    ORIGINAL = "original"
    OBSERVED = "observed"
    DERIVED = "derived"
    SIMULATED = "simulated"
    PROPOSED = "proposed"


@dataclass(frozen=True)
class Observation:
    """Metadata for an observation; large media payloads stay in external blobs.

    timestamp_ns is a source-clock timestamp, not automatically wall-clock time.
    clock_id identifies the clock domain so synchronization uncertainty is explicit.
    """
    observation_id: str
    kind: ObservationKind
    source_class: SourceClass
    timestamp_ns: int
    clock_id: str
    payload_ref: str
    content_sha256: str
    confidence_milli: int = 1000
    schema_version: str = "mirrorfield-observation.v0"

    def __post_init__(self) -> None:
        if not self.observation_id or not self.clock_id or not self.payload_ref:
            raise ValueError("observation_id, clock_id, and payload_ref are required")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if len(self.content_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.content_sha256
        ):
            raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")
        if not 0 <= self.confidence_milli <= 1000:
            raise ValueError("confidence_milli must be between 0 and 1000")
        if self.schema_version != "mirrorfield-observation.v0":
            raise ValueError("unsupported observation schema_version")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["kind"] = self.kind.value
        result["source_class"] = self.source_class.value
        return result
