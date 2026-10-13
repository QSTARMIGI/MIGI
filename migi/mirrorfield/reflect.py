"""Numerical reflection utilities: compare prediction with measured features."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence


@dataclass(frozen=True)
class Residual:
    feature_count: int
    mae_micro_units: int
    mse_micro_units_squared: int
    max_abs_micro_units: int
    schema_version: str = "mirrorfield-residual.v0"

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "feature_count": self.feature_count,
            "mae_micro_units": self.mae_micro_units,
            "mse_micro_units_squared": self.mse_micro_units_squared,
            "max_abs_micro_units": self.max_abs_micro_units,
        }


def compare_numeric_features(observed: Sequence[float],
                             predicted: Sequence[float]) -> Residual:
    """Compare equal-length finite feature vectors.

    Metrics are quantized to integer micro-units so they can be serialized by
    MIGI's current deterministic JSON canonicalizer, which rejects floats.
    Inputs must already share units and feature ordering.
    """
    if len(observed) != len(predicted):
        raise ValueError("observed and predicted vectors must have equal length")
    if not observed:
        raise ValueError("feature vectors must not be empty")
    errors = []
    for actual, estimate in zip(observed, predicted):
        if not isfinite(actual) or not isfinite(estimate):
            raise ValueError("feature values must be finite")
        errors.append(actual - estimate)
    abs_errors = [abs(value) for value in errors]
    mae = sum(abs_errors) / len(errors)
    mse = sum(value * value for value in errors) / len(errors)
    return Residual(
        feature_count=len(errors),
        mae_micro_units=round(mae * 1_000_000),
        mse_micro_units_squared=round(mse * 1_000_000_000_000),
        max_abs_micro_units=round(max(abs_errors) * 1_000_000),
    )
