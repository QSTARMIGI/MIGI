"""Shared multimodal state assembled from references to observations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .schema import Observation


@dataclass(frozen=True)
class MirrorState:
    state_id: str
    created_at_ns: int
    observations: tuple[Observation, ...]
    schema_version: str = "mirrorfield-state.v0"

    def __post_init__(self) -> None:
        if not self.state_id:
            raise ValueError("state_id is required")
        if self.created_at_ns < 0:
            raise ValueError("created_at_ns must be non-negative")
        ids = [item.observation_id for item in self.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("observation IDs must be unique within a state")

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "state_id": self.state_id,
            "created_at_ns": self.created_at_ns,
            "observations": [item.to_dict() for item in self.observations],
        }


def build_state(state_id: str, created_at_ns: int,
                observations: Iterable[Observation]) -> MirrorState:
    """Create deterministic ordering without claiming sensor-clock synchronization."""
    ordered = tuple(sorted(observations, key=lambda o: (
        o.timestamp_ns, o.clock_id, o.observation_id
    )))
    return MirrorState(state_id, created_at_ns, ordered)
