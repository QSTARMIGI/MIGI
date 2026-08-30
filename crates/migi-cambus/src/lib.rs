use migi_core::MuefEvent;
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::time::Duration;
use thiserror::Error;
use uuid::Uuid;

pub const CAMBUS_PROTOCOL_VERSION: &str = "cambus.v0";
pub const DEFAULT_MAX_FRAME_BYTES: usize = 1024 * 1024;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DeliveryClass {
    BestEffort,
    Reliable,
    Control,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct QosProfile {
    pub delivery: DeliveryClass,
    pub priority: u8,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_latency_ms: Option<u64>,
    pub local_only: bool,
}

impl Default for QosProfile {
    fn default() -> Self {
        Self {
            delivery: DeliveryClass::Reliable,
            priority: 128,
            max_latency_ms: None,
            local_only: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbolPacket {
    pub protocol_version: String,
    pub packet_id: String,
    pub correlation_id: String,
    pub source_node: String,
    pub destination_node: String,
    pub qos: QosProfile,
    pub event: MuefEvent,
}

impl SymbolPacket {
    pub fn new(
        source_node: impl Into<String>,
        destination_node: impl Into<String>,
        event: MuefEvent,
    ) -> Self {
        let packet_id = Uuid::new_v4().to_string();
        Self {
            protocol_version: CAMBUS_PROTOCOL_VERSION.into(),
            correlation_id: packet_id.clone(),
            packet_id,
            source_node: source_node.into(),
            destination_node: destination_node.into(),
            qos: QosProfile::default(),
            event,
        }
    }
}

pub fn encode_packet(packet: &SymbolPacket) -> Result<Vec<u8>, CambusError> {
    if packet.protocol_version != CAMBUS_PROTOCOL_VERSION {
        return Err(CambusError::UnsupportedVersion(packet.protocol_version.clone()));
    }
    Ok(serde_json::to_vec(packet)?)
}

pub fn decode_packet(bytes: &[u8]) -> Result<SymbolPacket, CambusError> {
    if bytes.len() > DEFAULT_MAX_FRAME_BYTES {
        return Err(CambusError::FrameTooLarge(bytes.len()));
    }
    let packet: SymbolPacket = serde_json::from_slice(bytes)?;
    if packet.protocol_version != CAMBUS_PROTOCOL_VERSION {
        return Err(CambusError::UnsupportedVersion(packet.protocol_version));
    }
    Ok(packet)
}

/// Length-prefixed CAMbus v0 frame over an arbitrary Read/Write stream.
/// The wire envelope is transport-neutral; TCP is only the first adapter.
pub fn write_frame<W: Write>(writer: &mut W, packet: &SymbolPacket) -> Result<(), CambusError> {
    let payload = encode_packet(packet)?;
    if payload.len() > DEFAULT_MAX_FRAME_BYTES {
        return Err(CambusError::FrameTooLarge(payload.len()));
    }
    let length = u32::try_from(payload.len()).map_err(|_| CambusError::FrameTooLarge(payload.len()))?;
    writer.write_all(&length.to_be_bytes())?;
    writer.write_all(&payload)?;
    writer.flush()?;
    Ok(())
}

pub fn read_frame<R: Read>(reader: &mut R) -> Result<SymbolPacket, CambusError> {
    let mut length_bytes = [0u8; 4];
    reader.read_exact(&mut length_bytes)?;
    let length = u32::from_be_bytes(length_bytes) as usize;
    if length > DEFAULT_MAX_FRAME_BYTES {
        return Err(CambusError::FrameTooLarge(length));
    }
    let mut payload = vec![0u8; length];
    reader.read_exact(&mut payload)?;
    decode_packet(&payload)
}

pub fn send_tcp(address: &str, packet: &SymbolPacket) -> Result<(), CambusError> {
    let mut stream = TcpStream::connect(address)?;
    stream.set_write_timeout(Some(Duration::from_secs(5)))?;
    write_frame(&mut stream, packet)
}

pub fn receive_one_tcp(listener: &TcpListener) -> Result<SymbolPacket, CambusError> {
    let (mut stream, _) = listener.accept()?;
    stream.set_read_timeout(Some(Duration::from_secs(5)))?;
    read_frame(&mut stream)
}

#[derive(Debug, Error)]
pub enum CambusError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("unsupported CAMbus protocol version: {0}")]
    UnsupportedVersion(String),
    #[error("CAMbus frame exceeds maximum size: {0} bytes")]
    FrameTooLarge(usize),
}

#[cfg(test)]
mod tests {
    use super::*;
    use migi_core::{Actor, ActorType, SourceClass};
    use std::thread;

    fn test_event() -> MuefEvent {
        let actor = Actor { actor_type: ActorType::Service, id: "node-a".into() };
        let mut event = MuefEvent::new("migi.signal.test", actor, SourceClass::Original);
        event.payload.insert("message".into(), serde_json::json!("hello-node-b"));
        event
    }

    #[test]
    fn packet_round_trip_preserves_event_identity() {
        let packet = SymbolPacket::new("node-a", "node-b", test_event());
        let bytes = encode_packet(&packet).unwrap();
        let decoded = decode_packet(&bytes).unwrap();
        assert_eq!(decoded.packet_id, packet.packet_id);
        assert_eq!(decoded.event.event_id, packet.event.event_id);
        assert_eq!(decoded.destination_node, "node-b");
    }

    #[test]
    fn two_nodes_exchange_muef_event_over_tcp() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();

        let receiver = thread::spawn(move || {
            let packet = receive_one_tcp(&listener).unwrap();
            assert_eq!(packet.source_node, "node-a");
            assert_eq!(packet.destination_node, "node-b");
            assert_eq!(packet.event.event_type, "migi.signal.test");
            packet.event.event_id
        });

        let packet = SymbolPacket::new("node-a", "node-b", test_event());
        let expected_event_id = packet.event.event_id.clone();
        send_tcp(&address.to_string(), &packet).unwrap();

        assert_eq!(receiver.join().unwrap(), expected_event_id);
    }
}
