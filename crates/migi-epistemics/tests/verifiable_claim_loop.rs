use migi_chainlog::{ChainLog, GENESIS_RECEIPT_REF};
use migi_core::{issue_receipt, Actor, ActorType, Authority, MuefEvent, SourceClass, TreLogic};
use migi_epistemics::{
    evaluate_evidence, qualify_factual_claim, rag0shot_score, ClaimQualification,
    ClaimRequirements, EvidenceItem, EvidenceState, LufitProfile, ProfileStatus,
    RetrievalSignals, SfoObservation, SfoRecord,
};
use serde_json::json;
use std::collections::BTreeSet;

fn set(values: &[&str]) -> BTreeSet<String> {
    values.iter().map(|value| (*value).to_string()).collect()
}

#[test]
fn observation_to_receipt_to_qualified_claim_is_verifiable() {
    let evidence = vec![
        EvidenceItem {
            direction: 1.0,
            confidence: 0.98,
            reliability: 0.95,
            provenance_quality: 1.0,
        },
        EvidenceItem {
            direction: 0.9,
            confidence: 0.90,
            reliability: 0.90,
            provenance_quality: 0.90,
        },
        EvidenceItem {
            direction: -1.0,
            confidence: 0.80,
            reliability: 0.20,
            provenance_quality: 0.20,
        },
    ];
    let assessment = evaluate_evidence(&evidence, 0.60).unwrap();
    assert_eq!(assessment.state, EvidenceState::Supported);

    let profile = LufitProfile {
        resolution_level: 64.0,
        budget_units: 1_000,
        observables: set(&["temperature"]),
        methods: set(&["sensor-fusion"]),
        cutoff: 10.0,
    };
    let requirements = ClaimRequirements {
        required_resolution_level: 32.0,
        estimated_cost_units: 100,
        required_observables: set(&["temperature"]),
        method: "sensor-fusion".into(),
        regime_value: 2.0,
    };
    let profile_status = migi_epistemics::validate_profile(&profile, &requirements).unwrap();
    assert_eq!(profile_status, ProfileStatus::InProfile);

    let observation = SfoObservation {
        source_id: "sensor-a".into(),
        source_class: SourceClass::Observed,
        value: json!({"temperature_c": 21.5}),
        confidence: assessment.confidence,
        provenance_ref: Some("sensor:a:sample:1".into()),
    };
    let sfo = SfoRecord::new(
        json!({"mode": "sampling"}),
        json!({"mode": "qualified"}),
        observation,
    );
    let qualification = qualify_factual_claim(
        &sfo.observation.source_class,
        &profile_status,
        &assessment,
    );
    assert_eq!(qualification, ClaimQualification::Supported);

    let actor = Actor {
        actor_type: ActorType::Service,
        id: "migi-epistemics".into(),
    };
    let mut event = MuefEvent::new("migi.claim.qualify", actor, SourceClass::Observed);
    event.payload.insert("assessment".into(), serde_json::to_value(&assessment).unwrap());
    event.payload.insert("profile_status".into(), serde_json::to_value(&profile_status).unwrap());

    let output = json!({
        "sfo": sfo,
        "qualification": qualification,
    });
    let authority = Authority {
        tre_logic: TreLogic::Proceed,
        reason_code: "local_test_claim_allowed".into(),
        consent_scope: Some("migi-cs-002".into()),
    };
    let receipt = issue_receipt(&event, authority, &output, GENESIS_RECEIPT_REF).unwrap();

    let mut chainlog = ChainLog::open_memory().unwrap();
    chainlog.append(event, output, receipt).unwrap();
    chainlog.verify().unwrap();
    assert_eq!(chainlog.len().unwrap(), 1);
}

#[test]
fn simulation_never_silently_becomes_observation() {
    let assessment = evaluate_evidence(
        &[EvidenceItem {
            direction: 1.0,
            confidence: 1.0,
            reliability: 1.0,
            provenance_quality: 1.0,
        }],
        0.60,
    )
    .unwrap();
    let qualification = qualify_factual_claim(
        &SourceClass::Simulated,
        &ProfileStatus::InProfile,
        &assessment,
    );
    assert_eq!(qualification, ClaimQualification::SimulationOnly);
}

#[test]
fn lufit_rejects_claims_outside_declared_profile() {
    let profile = LufitProfile {
        resolution_level: 16.0,
        budget_units: 25,
        observables: set(&["camera"]),
        methods: set(&["vision"]),
        cutoff: 1.0,
    };
    let requirements = ClaimRequirements {
        required_resolution_level: 64.0,
        estimated_cost_units: 100,
        required_observables: set(&["camera", "imu"]),
        method: "sensor-fusion".into(),
        regime_value: 2.5,
    };
    let status = migi_epistemics::validate_profile(&profile, &requirements).unwrap();
    assert!(matches!(status, ProfileStatus::OutOfProfile(ref violations) if violations.len() == 5));
}

#[test]
fn rag0shot_weighting_beats_similarity_only_when_source_quality_matters() {
    let trusted = RetrievalSignals {
        semantic: 0.82,
        provenance: 1.0,
        reliability: 0.95,
        graph: 0.80,
        temporal: 0.90,
    };
    let untrusted = RetrievalSignals {
        semantic: 1.0,
        provenance: 0.10,
        reliability: 0.20,
        graph: 0.30,
        temporal: 0.90,
    };

    assert!(untrusted.semantic > trusted.semantic);
    assert!(rag0shot_score(&trusted).unwrap() > rag0shot_score(&untrusted).unwrap());
}

#[test]
fn hold_or_deny_cannot_issue_executed_receipt() {
    let actor = Actor {
        actor_type: ActorType::Service,
        id: "guard-test".into(),
    };
    let event = MuefEvent::new("migi.action.test", actor, SourceClass::Proposed);
    let output = json!({"executed": false});

    for tre_logic in [TreLogic::Hold, TreLogic::Deny] {
        let authority = Authority {
            tre_logic,
            reason_code: "blocked".into(),
            consent_scope: Some("migi-cs-002".into()),
        };
        assert!(issue_receipt(&event, authority, &output, GENESIS_RECEIPT_REF).is_err());
    }
}
