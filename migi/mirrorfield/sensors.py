"""Small sensor-ingest helpers; device capture adapters are intentionally separate."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimedReference:
    stream: str
    timestamp_ns: int
    clock_id: str
    payload_ref: str

    def __post_init__(self) -> None:
        if not self.stream or not self.clock_id or not self.payload_ref:
            raise ValueError("stream, clock_id, and payload_ref are required")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")


@dataclass(frozen=True)
class Alignment:
    left: TimedReference
    right: TimedReference
    delta_ns: int
    comparable: bool
    reason: str


def align_pair(left: TimedReference, right: TimedReference, tolerance_ns: int) -> Alignment:
    """Compare timestamps only when they use the same clock domain.

    This does not estimate clock offsets. Different clock IDs require a calibrated
    synchronization transform before their timestamps can be compared.
    """
    if tolerance_ns < 0:
        raise ValueError("tolerance_ns must be non-negative")
    if left.clock_id != right.clock_id:
        return Alignment(left, right, 0, False, "clock_domain_mismatch")
    delta = right.timestamp_ns - left.timestamp_ns
    if abs(delta) > tolerance_ns:
        return Alignment(left, right, delta, False, "outside_tolerance")
    return Alignment(left, right, delta, True, "aligned_within_tolerance")
