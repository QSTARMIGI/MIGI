"""Mirrorfield v0.1: auditable multimodal observation and state comparison.

This package is a software architecture prototype, not a claim of a new
physical field. Raw observations and derived interpretations stay distinct.
"""
from .schema import Observation, ObservationKind, SourceClass
from .state import MirrorState, build_state
from .reflect import Residual, compare_numeric_features
from .receipts import make_receipt, verify_receipt

__all__ = [
    "Observation", "ObservationKind", "SourceClass", "MirrorState",
    "build_state", "Residual", "compare_numeric_features",
    "make_receipt", "verify_receipt",
]
