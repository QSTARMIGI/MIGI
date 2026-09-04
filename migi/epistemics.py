from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from .models import SourceClass


class EvidenceState(str, Enum):
    SUPPORTED = "+1"
    UNRESOLVED = "0"
    CONTRADICTED = "-1"


class ClaimQualification(str, Enum):
    SUPPORTED = "supported"
    UNRESOLVED = "unresolved"
    CONTRADICTED = "contradicted"
    OUT_OF_PROFILE = "out_of_profile"
    SIMULATION_ONLY = "simulation_only"


@dataclass(frozen=True)
class EvidenceItem:
    """One bounded piece of evidence.

    direction is in [-1, 1]: -1 contradicts, 0 is neutral/unknown, +1 supports.
    confidence, reliability, and provenance_quality are in [0, 1].
    """

    direction: float
    confidence: float
    reliability: float
    provenance_quality: float

    def validate(self) -> None:
        if not math.isfinite(self.direction) or not -1.0 <= self.direction <= 1.0:
            raise ValueError("evidence direction must be finite and in [-1, 1]")
        for name, value in (
            ("confidence", self.confidence),
            ("reliability", self.reliability),
            ("provenance_quality", self.provenance_quality),
        ):
            if not _unit_interval(value):
                raise ValueError(f"evidence {name} must be finite and in [0, 1]")


@dataclass(frozen=True)
class EvidenceAssessment:
    state: str
    support_score: float
    confidence: float
    uncertainty: float
    probabilities: tuple[float, float, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "support_score": self.support_score,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "probabilities": {
                "contradicted": self.probabilities[0],
                "unresolved": self.probabilities[1],
                "supported": self.probabilities[2],
            },
        }


@dataclass(frozen=True)
class SFOObservation:
    source_id: str
    source_class: str
    value: Any
    confidence: float
    provenance_ref: str | None = None

    def validate(self) -> None:
        if not self.source_id:
            raise ValueError("SFO observation source_id is required")
        valid_classes = {value.value for value in SourceClass}
        if self.source_class not in valid_classes:
            raise ValueError(f"unsupported SFO source_class: {self.source_class}")
        if not _unit_interval(self.confidence):
            raise ValueError("SFO observation confidence must be finite and in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class SFORecord:
    state_before: Any
    state_after: Any
    observation: SFOObservation

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_before": self.state_before,
            "state_after": self.state_after,
            "observation": self.observation.to_dict(),
        }


@dataclass(frozen=True)
class LUFITProfile:
    """Executable v0 LUFIT validity profile.

    Higher resolution_level means a finer/more capable declared resolution.
    cutoff is the absolute regime boundary for the profile.
    """

    resolution_level: float
    budget_units: int
    observables: frozenset[str]
    methods: frozenset[str]
    cutoff: float

    @classmethod
    def create(
        cls,
        *,
        resolution_level: float,
        budget_units: int,
        observables: Iterable[str],
        methods: Iterable[str],
        cutoff: float,
    ) -> "LUFITProfile":
        return cls(
            resolution_level=resolution_level,
            budget_units=budget_units,
            observables=frozenset(observables),
            methods=frozenset(methods),
            cutoff=cutoff,
        )


@dataclass(frozen=True)
class ClaimRequirements:
    required_resolution_level: float
    estimated_cost_units: int
    required_observables: frozenset[str]
    method: str
    regime_value: float

    @classmethod
    def create(
        cls,
        *,
        required_resolution_level: float,
        estimated_cost_units: int,
        required_observables: Iterable[str],
        method: str,
        regime_value: float,
    ) -> "ClaimRequirements":
        return cls(
            required_resolution_level=required_resolution_level,
            estimated_cost_units=estimated_cost_units,
            required_observables=frozenset(required_observables),
            method=method,
            regime_value=regime_value,
        )


@dataclass(frozen=True)
class ProfileStatus:
    in_profile: bool
    violations: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "in_profile" if self.in_profile else "out_of_profile",
            "violations": list(self.violations),
        }


@dataclass(frozen=True)
class RetrievalSignals:
    semantic: float
    provenance: float
    reliability: float
    graph: float
    temporal: float

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not _unit_interval(float(value)):
                raise ValueError(f"retrieval signal {name} must be finite and in [0, 1]")


def evaluate_evidence(evidence: Iterable[EvidenceItem], *, threshold: float = 0.60) -> EvidenceAssessment:
    if not _unit_interval(threshold):
        raise ValueError("evidence threshold must be finite and in [0, 1]")

    contradicted = 0.0
    unresolved = 0.0
    supported = 0.0

    for item in evidence:
        item.validate()
        weight = item.confidence * item.reliability * item.provenance_quality
        supported += weight * max(item.direction, 0.0)
        contradicted += weight * max(-item.direction, 0.0)
        unresolved += weight * (1.0 - abs(item.direction))

    total = contradicted + unresolved + supported
    if total <= float.fromhex("0x1.0p-52"):
        probabilities = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    else:
        probabilities = (contradicted / total, unresolved / total, supported / total)

    support_score = probabilities[2] - probabilities[0]
    if support_score > threshold:
        state = EvidenceState.SUPPORTED.value
    elif support_score < -threshold:
        state = EvidenceState.CONTRADICTED.value
    else:
        state = EvidenceState.UNRESOLVED.value

    confidence = max(probabilities[0], probabilities[2])
    entropy = -sum(p * math.log2(p) for p in probabilities if p > 0.0)
    uncertainty = entropy / math.log2(3.0)

    return EvidenceAssessment(
        state=state,
        support_score=support_score,
        confidence=confidence,
        uncertainty=uncertainty,
        probabilities=probabilities,
    )


def validate_profile(profile: LUFITProfile, requirements: ClaimRequirements) -> ProfileStatus:
    if (
        not math.isfinite(profile.resolution_level)
        or profile.resolution_level < 0.0
        or profile.budget_units < 0
        or not math.isfinite(profile.cutoff)
        or profile.cutoff < 0.0
        or not math.isfinite(requirements.required_resolution_level)
        or requirements.required_resolution_level < 0.0
        or requirements.estimated_cost_units < 0
        or not math.isfinite(requirements.regime_value)
    ):
        raise ValueError("LUFIT profile and claim requirements must use finite non-negative bounds")

    violations: list[dict[str, Any]] = []
    if profile.resolution_level < requirements.required_resolution_level:
        violations.append(
            {
                "code": "insufficient_resolution",
                "available": profile.resolution_level,
                "required": requirements.required_resolution_level,
            }
        )
    if profile.budget_units < requirements.estimated_cost_units:
        violations.append(
            {
                "code": "budget_exceeded",
                "available": profile.budget_units,
                "required": requirements.estimated_cost_units,
            }
        )
    for observable in sorted(requirements.required_observables - profile.observables):
        violations.append({"code": "missing_observable", "observable": observable})
    if requirements.method not in profile.methods:
        violations.append({"code": "method_not_allowed", "method": requirements.method})
    if abs(requirements.regime_value) > profile.cutoff:
        violations.append(
            {
                "code": "cutoff_exceeded",
                "cutoff": profile.cutoff,
                "value": requirements.regime_value,
            }
        )

    return ProfileStatus(in_profile=not violations, violations=tuple(violations))


def qualify_factual_claim(
    *,
    source_class: str,
    profile_status: ProfileStatus,
    assessment: EvidenceAssessment,
) -> str:
    if not profile_status.in_profile:
        return ClaimQualification.OUT_OF_PROFILE.value
    if source_class == SourceClass.SIMULATED.value:
        return ClaimQualification.SIMULATION_ONLY.value
    if assessment.state == EvidenceState.SUPPORTED.value:
        return ClaimQualification.SUPPORTED.value
    if assessment.state == EvidenceState.CONTRADICTED.value:
        return ClaimQualification.CONTRADICTED.value
    return ClaimQualification.UNRESOLVED.value


def rag0shot_score(signals: RetrievalSignals) -> float:
    signals.validate()
    return (
        0.40 * signals.semantic
        + 0.20 * signals.provenance
        + 0.15 * signals.reliability
        + 0.15 * signals.graph
        + 0.10 * signals.temporal
    )


def rank_candidates(candidates: Iterable[tuple[str, RetrievalSignals]]) -> list[tuple[str, float]]:
    ranked = [(candidate_id, rag0shot_score(signals)) for candidate_id, signals in candidates]
    return sorted(ranked, key=lambda item: (-item[1], item[0]))


def _unit_interval(value: float) -> bool:
    return math.isfinite(value) and 0.0 <= value <= 1.0
