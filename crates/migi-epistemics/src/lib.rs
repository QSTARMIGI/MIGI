use migi_core::SourceClass;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeSet;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum EvidenceState {
    #[serde(rename = "+1")]
    Supported,
    #[serde(rename = "0")]
    Unresolved,
    #[serde(rename = "-1")]
    Contradicted,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EvidenceItem {
    /// -1.0 = contradicts, 0.0 = neutral/unknown, +1.0 = supports.
    pub direction: f64,
    pub confidence: f64,
    pub reliability: f64,
    pub provenance_quality: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EvidenceAssessment {
    pub state: EvidenceState,
    /// Net support in [-1, 1].
    pub support_score: f64,
    /// Probability mass assigned to a supported or contradicted claim, whichever is larger.
    pub confidence: f64,
    /// Normalized Shannon entropy across contradicted / unresolved / supported mass.
    pub uncertainty: f64,
    /// [contradicted, unresolved, supported]
    pub probabilities: [f64; 3],
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SfoObservation {
    pub source_id: String,
    pub source_class: SourceClass,
    pub value: Value,
    pub confidence: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provenance_ref: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SfoRecord {
    pub state_before: Value,
    pub state_after: Value,
    pub observation: SfoObservation,
}

impl SfoRecord {
    pub fn new(state_before: Value, state_after: Value, observation: SfoObservation) -> Self {
        Self { state_before, state_after, observation }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LufitProfile {
    /// Higher means a finer/more capable declared resolution level.
    pub resolution_level: f64,
    pub budget_units: u64,
    pub observables: BTreeSet<String>,
    pub methods: BTreeSet<String>,
    /// Absolute regime bound for this profile.
    pub cutoff: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ClaimRequirements {
    pub required_resolution_level: f64,
    pub estimated_cost_units: u64,
    pub required_observables: BTreeSet<String>,
    pub method: String,
    pub regime_value: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ProfileViolation {
    InsufficientResolution { available: f64, required: f64 },
    BudgetExceeded { available: u64, required: u64 },
    MissingObservable(String),
    MethodNotAllowed(String),
    CutoffExceeded { cutoff: f64, value: f64 },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ProfileStatus {
    InProfile,
    OutOfProfile(Vec<ProfileViolation>),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ClaimQualification {
    Supported,
    Unresolved,
    Contradicted,
    OutOfProfile,
    SimulationOnly,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RetrievalSignals {
    pub semantic: f64,
    pub provenance: f64,
    pub reliability: f64,
    pub graph: f64,
    pub temporal: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RetrievalCandidate {
    pub id: String,
    pub signals: RetrievalSignals,
}

#[derive(Debug, Error)]
pub enum EpistemicsError {
    #[error("evidence direction must be finite and in [-1, 1]")]
    InvalidDirection,
    #[error("evidence confidence/reliability/provenance values must be finite and in [0, 1]")]
    InvalidEvidenceWeight,
    #[error("threshold must be finite and in [0, 1]")]
    InvalidThreshold,
    #[error("LUFIT profile and claim requirements must contain finite non-negative resolution/cutoff values")]
    InvalidProfile,
    #[error("retrieval signals must be finite and in [0, 1]")]
    InvalidRetrievalSignal,
}

fn unit_interval(value: f64) -> bool {
    value.is_finite() && (0.0..=1.0).contains(&value)
}

pub fn evaluate_evidence(
    evidence: &[EvidenceItem],
    threshold: f64,
) -> Result<EvidenceAssessment, EpistemicsError> {
    if !unit_interval(threshold) {
        return Err(EpistemicsError::InvalidThreshold);
    }

    let mut contradicted = 0.0;
    let mut unresolved = 0.0;
    let mut supported = 0.0;

    for item in evidence {
        if !item.direction.is_finite() || !(-1.0..=1.0).contains(&item.direction) {
            return Err(EpistemicsError::InvalidDirection);
        }
        if !unit_interval(item.confidence)
            || !unit_interval(item.reliability)
            || !unit_interval(item.provenance_quality)
        {
            return Err(EpistemicsError::InvalidEvidenceWeight);
        }

        let weight = item.confidence * item.reliability * item.provenance_quality;
        supported += weight * item.direction.max(0.0);
        contradicted += weight * (-item.direction).max(0.0);
        unresolved += weight * (1.0 - item.direction.abs());
    }

    let total = contradicted + unresolved + supported;
    let probabilities = if total <= f64::EPSILON {
        [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0]
    } else {
        [contradicted / total, unresolved / total, supported / total]
    };

    let support_score = probabilities[2] - probabilities[0];
    let state = if support_score > threshold {
        EvidenceState::Supported
    } else if support_score < -threshold {
        EvidenceState::Contradicted
    } else {
        EvidenceState::Unresolved
    };

    let confidence = probabilities[0].max(probabilities[2]);
    let entropy = probabilities
        .iter()
        .filter(|p| **p > 0.0)
        .map(|p| -p * p.log2())
        .sum::<f64>();
    let uncertainty = entropy / 3.0_f64.log2();

    Ok(EvidenceAssessment {
        state,
        support_score,
        confidence,
        uncertainty,
        probabilities,
    })
}

pub fn validate_profile(
    profile: &LufitProfile,
    requirements: &ClaimRequirements,
) -> Result<ProfileStatus, EpistemicsError> {
    if !profile.resolution_level.is_finite()
        || profile.resolution_level < 0.0
        || !profile.cutoff.is_finite()
        || profile.cutoff < 0.0
        || !requirements.required_resolution_level.is_finite()
        || requirements.required_resolution_level < 0.0
        || !requirements.regime_value.is_finite()
    {
        return Err(EpistemicsError::InvalidProfile);
    }

    let mut violations = Vec::new();
    if profile.resolution_level < requirements.required_resolution_level {
        violations.push(ProfileViolation::InsufficientResolution {
            available: profile.resolution_level,
            required: requirements.required_resolution_level,
        });
    }
    if profile.budget_units < requirements.estimated_cost_units {
        violations.push(ProfileViolation::BudgetExceeded {
            available: profile.budget_units,
            required: requirements.estimated_cost_units,
        });
    }
    for observable in &requirements.required_observables {
        if !profile.observables.contains(observable) {
            violations.push(ProfileViolation::MissingObservable(observable.clone()));
        }
    }
    if !profile.methods.contains(&requirements.method) {
        violations.push(ProfileViolation::MethodNotAllowed(requirements.method.clone()));
    }
    if requirements.regime_value.abs() > profile.cutoff {
        violations.push(ProfileViolation::CutoffExceeded {
            cutoff: profile.cutoff,
            value: requirements.regime_value,
        });
    }

    Ok(if violations.is_empty() {
        ProfileStatus::InProfile
    } else {
        ProfileStatus::OutOfProfile(violations)
    })
}

pub fn qualify_factual_claim(
    source_class: &SourceClass,
    profile_status: &ProfileStatus,
    assessment: &EvidenceAssessment,
) -> ClaimQualification {
    if matches!(profile_status, ProfileStatus::OutOfProfile(_)) {
        return ClaimQualification::OutOfProfile;
    }
    if matches!(source_class, SourceClass::Simulated) {
        return ClaimQualification::SimulationOnly;
    }

    match assessment.state {
        EvidenceState::Supported => ClaimQualification::Supported,
        EvidenceState::Unresolved => ClaimQualification::Unresolved,
        EvidenceState::Contradicted => ClaimQualification::Contradicted,
    }
}

pub fn rag0shot_score(signals: &RetrievalSignals) -> Result<f64, EpistemicsError> {
    let values = [
        signals.semantic,
        signals.provenance,
        signals.reliability,
        signals.graph,
        signals.temporal,
    ];
    if values.iter().any(|value| !unit_interval(*value)) {
        return Err(EpistemicsError::InvalidRetrievalSignal);
    }

    Ok(0.40 * signals.semantic
        + 0.20 * signals.provenance
        + 0.15 * signals.reliability
        + 0.15 * signals.graph
        + 0.10 * signals.temporal)
}

pub fn rank_candidates(
    candidates: &[RetrievalCandidate],
) -> Result<Vec<(String, f64)>, EpistemicsError> {
    let mut ranked = candidates
        .iter()
        .map(|candidate| Ok((candidate.id.clone(), rag0shot_score(&candidate.signals)?)))
        .collect::<Result<Vec<_>, EpistemicsError>>()?;
    ranked.sort_by(|a, b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    Ok(ranked)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_evidence_is_unresolved_and_maximally_uncertain() {
        let assessment = evaluate_evidence(&[], 0.60).unwrap();
        assert_eq!(assessment.state, EvidenceState::Unresolved);
        assert!((assessment.uncertainty - 1.0).abs() < 1e-12);
    }

    #[test]
    fn simulated_source_cannot_become_factual_observation() {
        let assessment = EvidenceAssessment {
            state: EvidenceState::Supported,
            support_score: 0.9,
            confidence: 0.95,
            uncertainty: 0.1,
            probabilities: [0.02, 0.03, 0.95],
        };
        assert_eq!(
            qualify_factual_claim(&SourceClass::Simulated, &ProfileStatus::InProfile, &assessment),
            ClaimQualification::SimulationOnly
        );
    }

    #[test]
    fn provenance_can_outweigh_raw_semantic_similarity() {
        let trusted = RetrievalSignals {
            semantic: 0.82,
            provenance: 1.0,
            reliability: 0.95,
            graph: 0.8,
            temporal: 0.9,
        };
        let superficially_similar = RetrievalSignals {
            semantic: 1.0,
            provenance: 0.1,
            reliability: 0.2,
            graph: 0.3,
            temporal: 0.9,
        };
        assert!(rag0shot_score(&trusted).unwrap() > rag0shot_score(&superficially_similar).unwrap());
    }
}
