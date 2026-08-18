use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ActorType {
    User,
    Agent,
    Service,
    Device,
    Organization,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Actor {
    #[serde(rename = "type")]
    pub actor_type: ActorType,
    pub id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum SourceClass {
    Original,
    Observed,
    Derived,
    Simulated,
    Proposed,
    Authorized,
    Executed,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum TreLogic {
    #[serde(rename = "+1")]
    Proceed,
    #[serde(rename = "0")]
    Hold,
    #[serde(rename = "-1")]
    Deny,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Authority {
    pub tre_logic: TreLogic,
    pub reason_code: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub consent_scope: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MuefEvent {
    pub schema_version: String,
    pub event_id: String,
    pub event_type: String,
    pub occurred_at: DateTime<Utc>,
    pub actor: Actor,
    pub source_class: SourceClass,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authority: Option<Authority>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_event_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub receipt_id: Option<String>,
    pub payload: serde_json::Map<String, serde_json::Value>,
}

impl MuefEvent {
    pub fn new(event_type: impl Into<String>, actor: Actor, source_class: SourceClass) -> Self {
        Self {
            schema_version: "muef.v0".into(),
            event_id: Uuid::new_v4().to_string(),
            event_type: event_type.into(),
            occurred_at: Utc::now(),
            actor,
            source_class,
            authority: None,
            parent_event_id: None,
            receipt_id: None,
            payload: serde_json::Map::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigiReceipt {
    pub schema_version: String,
    pub receipt_id: String,
    pub issued_at: DateTime<Utc>,
    pub event_id: String,
    pub source_class: SourceClass,
    pub intent_ref: String,
    pub output_ref: String,
    pub previous_receipt_ref: String,
    pub authority: Authority,
    pub input_hash: String,
    pub output_hash: String,
}

#[derive(Debug, Error)]
pub enum CoreError {
    #[error("event schema_version must be muef.v0")]
    InvalidSchemaVersion,
    #[error("event_type must be namespaced, e.g. migi.signal.test")]
    InvalidEventType,
    #[error("event payload must be an object")]
    InvalidPayload,
}

pub fn validate_event(event: &MuefEvent) -> Result<(), CoreError> {
    if event.schema_version != "muef.v0" {
        return Err(CoreError::InvalidSchemaVersion);
    }
    let parts: Vec<&str> = event.event_type.split('.').collect();
    if parts.len() < 2 || parts.iter().any(|p| p.is_empty() || !p.chars().next().unwrap().is_ascii_lowercase()) {
        return Err(CoreError::InvalidEventType);
    }
    Ok(())
}

pub fn sha256_json<T: Serialize>(value: &T) -> String {
    let bytes = serde_json::to_vec(value).expect("serializable value");
    let digest = Sha256::digest(bytes);
    format!("sha256:{digest:x}")
}

pub fn issue_receipt(
    event: &MuefEvent,
    authority: Authority,
    output: &serde_json::Value,
    previous_receipt_ref: impl Into<String>,
) -> Result<MigiReceipt, CoreError> {
    validate_event(event)?;
    let input_hash = sha256_json(event);
    let output_hash = sha256_json(output);
    Ok(MigiReceipt {
        schema_version: "migi-receipt.v0".into(),
        receipt_id: Uuid::new_v4().to_string(),
        issued_at: Utc::now(),
        event_id: event.event_id.clone(),
        source_class: SourceClass::Executed,
        intent_ref: event.event_id.clone(),
        output_ref: output_hash.clone(),
        previous_receipt_ref: previous_receipt_ref.into(),
        authority,
        input_hash,
        output_hash,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn actor() -> Actor {
        Actor { actor_type: ActorType::Service, id: "migi-test-node".into() }
    }

    #[test]
    fn muef_event_validates() {
        let event = MuefEvent::new("migi.signal.test", actor(), SourceClass::Original);
        assert!(validate_event(&event).is_ok());
    }

    #[test]
    fn receipt_chains_event_and_hashes_output() {
        let event = MuefEvent::new("migi.signal.test", actor(), SourceClass::Original);
        let authority = Authority { tre_logic: TreLogic::Proceed, reason_code: "test_allowed".into(), consent_scope: None };
        let output = serde_json::json!({"message": "hello"});
        let receipt = issue_receipt(&event, authority, &output, "genesis").unwrap();
        assert_eq!(receipt.event_id, event.event_id);
        assert!(receipt.input_hash.starts_with("sha256:"));
        assert!(receipt.output_hash.starts_with("sha256:"));
        assert_eq!(receipt.previous_receipt_ref, "genesis");
    }

    #[test]
    fn tre_logic_serializes_to_protocol_values() {
        assert_eq!(serde_json::to_string(&TreLogic::Proceed).unwrap(), "\"+1\"");
        assert_eq!(serde_json::to_string(&TreLogic::Hold).unwrap(), "\"0\"");
        assert_eq!(serde_json::to_string(&TreLogic::Deny).unwrap(), "\"-1\"");
    }
}
