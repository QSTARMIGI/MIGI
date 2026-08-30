use migi_core::{sha256_json, MigiReceipt, MuefEvent};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::Path;
use thiserror::Error;

pub const GENESIS_RECEIPT_REF: &str = "genesis";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainEntry {
    pub sequence: u64,
    pub event: MuefEvent,
    pub observation: Value,
    pub receipt: MigiReceipt,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct ReplayState {
    pub values: BTreeMap<String, Value>,
    pub applied_entries: u64,
    pub head_receipt_id: Option<String>,
}

impl ReplayState {
    /// Deterministic v0 state reducer.
    /// If an event payload contains `state_patch`, JSON null deletes a key;
    /// any other value sets it. Only verified entries are replayed.
    pub fn apply(&mut self, entry: &ChainEntry) {
        if let Some(Value::Object(patch)) = entry.event.payload.get("state_patch") {
            for (key, value) in patch {
                if value.is_null() {
                    self.values.remove(key);
                } else {
                    self.values.insert(key.clone(), value.clone());
                }
            }
        }
        self.applied_entries += 1;
        self.head_receipt_id = Some(entry.receipt.receipt_id.clone());
    }
}

pub struct ChainLog {
    conn: Connection,
}

impl ChainLog {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, ChainLogError> {
        let conn = Connection::open(path)?;
        let log = Self { conn };
        log.init()?;
        Ok(log)
    }

    pub fn open_memory() -> Result<Self, ChainLogError> {
        let conn = Connection::open_in_memory()?;
        let log = Self { conn };
        log.init()?;
        Ok(log)
    }

    fn init(&self) -> Result<(), ChainLogError> {
        self.conn.execute_batch(
            "PRAGMA foreign_keys = ON;
             CREATE TABLE IF NOT EXISTS chainlog (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                receipt_id TEXT NOT NULL UNIQUE,
                previous_receipt_ref TEXT NOT NULL,
                event_json TEXT NOT NULL,
                observation_json TEXT NOT NULL,
                receipt_json TEXT NOT NULL
             );
             CREATE INDEX IF NOT EXISTS idx_chainlog_receipt ON chainlog(receipt_id);
             CREATE INDEX IF NOT EXISTS idx_chainlog_event ON chainlog(event_id);"
        )?;
        Ok(())
    }

    pub fn len(&self) -> Result<u64, ChainLogError> {
        Ok(self.conn.query_row("SELECT COUNT(*) FROM chainlog", [], |row| row.get::<_, u64>(0))?)
    }

    pub fn head_receipt_id(&self) -> Result<Option<String>, ChainLogError> {
        let mut stmt = self.conn.prepare(
            "SELECT receipt_id FROM chainlog ORDER BY sequence DESC LIMIT 1"
        )?;
        let mut rows = stmt.query([])?;
        Ok(match rows.next()? {
            Some(row) => Some(row.get(0)?),
            None => None,
        })
    }

    pub fn expected_previous_receipt_ref(&self) -> Result<String, ChainLogError> {
        Ok(self.head_receipt_id()?.unwrap_or_else(|| GENESIS_RECEIPT_REF.to_string()))
    }

    pub fn append(
        &mut self,
        event: MuefEvent,
        observation: Value,
        receipt: MigiReceipt,
    ) -> Result<ChainEntry, ChainLogError> {
        let expected_previous = self.expected_previous_receipt_ref()?;
        verify_record(&event, &observation, &receipt, &expected_previous)?;

        let event_json = serde_json::to_string(&event)?;
        let observation_json = serde_json::to_string(&observation)?;
        let receipt_json = serde_json::to_string(&receipt)?;

        self.conn.execute(
            "INSERT INTO chainlog (
                event_id, receipt_id, previous_receipt_ref,
                event_json, observation_json, receipt_json
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                &event.event_id,
                &receipt.receipt_id,
                &receipt.previous_receipt_ref,
                &event_json,
                &observation_json,
                &receipt_json,
            ],
        )?;

        let sequence = self.conn.last_insert_rowid() as u64;
        Ok(ChainEntry { sequence, event, observation, receipt })
    }

    pub fn entries(&self) -> Result<Vec<ChainEntry>, ChainLogError> {
        let mut stmt = self.conn.prepare(
            "SELECT sequence, event_json, observation_json, receipt_json
             FROM chainlog ORDER BY sequence ASC"
        )?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, u64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
            ))
        })?;

        let mut entries = Vec::new();
        for row in rows {
            let (sequence, event_json, observation_json, receipt_json) = row?;
            entries.push(ChainEntry {
                sequence,
                event: serde_json::from_str(&event_json)?,
                observation: serde_json::from_str(&observation_json)?,
                receipt: serde_json::from_str(&receipt_json)?,
            });
        }
        Ok(entries)
    }

    pub fn verify(&self) -> Result<(), ChainLogError> {
        let entries = self.entries()?;
        let mut previous = GENESIS_RECEIPT_REF.to_string();
        for entry in entries {
            verify_record(&entry.event, &entry.observation, &entry.receipt, &previous)?;
            previous = entry.receipt.receipt_id;
        }
        Ok(())
    }

    pub fn replay(&self) -> Result<ReplayState, ChainLogError> {
        self.verify()?;
        let mut state = ReplayState::default();
        for entry in self.entries()? {
            state.apply(&entry);
        }
        Ok(state)
    }
}

pub fn verify_record(
    event: &MuefEvent,
    observation: &Value,
    receipt: &MigiReceipt,
    expected_previous_receipt_ref: &str,
) -> Result<(), ChainLogError> {
    if receipt.event_id != event.event_id {
        return Err(ChainLogError::EventReceiptMismatch);
    }
    if receipt.previous_receipt_ref != expected_previous_receipt_ref {
        return Err(ChainLogError::BrokenParent {
            expected: expected_previous_receipt_ref.to_string(),
            actual: receipt.previous_receipt_ref.clone(),
        });
    }

    let expected_input_hash = sha256_json(event);
    let recorded_input_hash = receipt
        .metadata
        .get("input_hash")
        .and_then(Value::as_str)
        .ok_or(ChainLogError::MissingInputHash)?;
    if recorded_input_hash != expected_input_hash {
        return Err(ChainLogError::InputHashMismatch);
    }

    let expected_output_hash = sha256_json(observation);
    if receipt.output_ref != expected_output_hash {
        return Err(ChainLogError::OutputHashMismatch);
    }

    if let Some(recorded_output_hash) = receipt.metadata.get("output_hash").and_then(Value::as_str) {
        if recorded_output_hash != expected_output_hash {
            return Err(ChainLogError::OutputHashMismatch);
        }
    }

    Ok(())
}

#[derive(Debug, Error)]
pub enum ChainLogError {
    #[error("SQLite error: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("receipt event_id does not match event")]
    EventReceiptMismatch,
    #[error("receipt parent mismatch: expected {expected}, got {actual}")]
    BrokenParent { expected: String, actual: String },
    #[error("receipt metadata is missing input_hash")]
    MissingInputHash,
    #[error("event input hash does not match receipt")]
    InputHashMismatch,
    #[error("observation output hash does not match receipt")]
    OutputHashMismatch,
}

#[cfg(test)]
mod tests {
    use super::*;
    use migi_core::{issue_receipt, Actor, ActorType, Authority, SourceClass, TreLogic};

    fn actor() -> Actor {
        Actor { actor_type: ActorType::Service, id: "node-a".into() }
    }

    fn authority() -> Authority {
        Authority {
            tre_logic: TreLogic::Proceed,
            reason_code: "test_allowed".into(),
            consent_scope: Some("local-test".into()),
        }
    }

    fn event_with_patch(key: &str, value: Value) -> MuefEvent {
        let mut event = MuefEvent::new("migi.state.patch", actor(), SourceClass::Original);
        event.payload.insert("state_patch".into(), serde_json::json!({key: value}));
        event
    }

    #[test]
    fn appends_verifies_and_replays_chain() {
        let mut log = ChainLog::open_memory().unwrap();

        let event1 = event_with_patch("mode", serde_json::json!("idle"));
        let observation1 = serde_json::json!({"accepted": true, "state": "idle"});
        let receipt1 = issue_receipt(&event1, authority(), &observation1, GENESIS_RECEIPT_REF).unwrap();
        log.append(event1, observation1, receipt1).unwrap();

        let event2 = event_with_patch("mode", serde_json::json!("active"));
        let observation2 = serde_json::json!({"accepted": true, "state": "active"});
        let previous = log.head_receipt_id().unwrap().unwrap();
        let receipt2 = issue_receipt(&event2, authority(), &observation2, previous).unwrap();
        log.append(event2, observation2, receipt2).unwrap();

        assert_eq!(log.len().unwrap(), 2);
        log.verify().unwrap();

        let state = log.replay().unwrap();
        assert_eq!(state.values.get("mode"), Some(&serde_json::json!("active")));
        assert_eq!(state.applied_entries, 2);
        assert!(state.head_receipt_id.is_some());
    }

    #[test]
    fn rejects_broken_parent_chain() {
        let mut log = ChainLog::open_memory().unwrap();
        let event = event_with_patch("mode", serde_json::json!("idle"));
        let observation = serde_json::json!({"accepted": true});
        let receipt = issue_receipt(&event, authority(), &observation, "wrong-parent").unwrap();
        let error = log.append(event, observation, receipt).unwrap_err();
        assert!(matches!(error, ChainLogError::BrokenParent { .. }));
    }

    #[test]
    fn rejects_tampered_observation() {
        let event = event_with_patch("mode", serde_json::json!("idle"));
        let original = serde_json::json!({"accepted": true});
        let receipt = issue_receipt(&event, authority(), &original, GENESIS_RECEIPT_REF).unwrap();
        let tampered = serde_json::json!({"accepted": false});
        let error = verify_record(&event, &tampered, &receipt, GENESIS_RECEIPT_REF).unwrap_err();
        assert!(matches!(error, ChainLogError::OutputHashMismatch));
    }
}
