from __future__ import annotations

import json
import socket
import struct
from dataclasses import asdict, dataclass, field
from typing import Any

from .canonical import canonical_json_bytes
from .events import MUEFEvent
from .util import new_id

CAMBUS_PROTOCOL_VERSION = "cambus.v0"
MAX_FRAME_BYTES = 1024 * 1024


@dataclass(frozen=True)
class QoSProfile:
    delivery: str = "reliable"
    priority: int = 128
    max_latency_ms: int | None = None
    local_only: bool = False

    def validate(self) -> None:
        if self.delivery not in {"best_effort", "reliable", "control"}:
            raise ValueError("Unsupported CAMbus delivery class")
        if not 0 <= self.priority <= 255:
            raise ValueError("CAMbus priority must be between 0 and 255")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ValueError("CAMbus max_latency_ms cannot be negative")


@dataclass(frozen=True)
class SymbolPacket:
    protocol_version: str
    packet_id: str
    correlation_id: str
    source_node: str
    destination_node: str
    event: MUEFEvent
    qos: QoSProfile = field(default_factory=QoSProfile)

    @classmethod
    def create(
        cls,
        *,
        source_node: str,
        destination_node: str,
        event: MUEFEvent,
        qos: QoSProfile | None = None,
        correlation_id: str | None = None,
    ) -> "SymbolPacket":
        packet_id = new_id("packet")
        packet = cls(
            protocol_version=CAMBUS_PROTOCOL_VERSION,
            packet_id=packet_id,
            correlation_id=correlation_id or packet_id,
            source_node=source_node,
            destination_node=destination_node,
            event=event,
            qos=qos or QoSProfile(),
        )
        packet.validate()
        return packet

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SymbolPacket":
        packet = cls(
            protocol_version=str(value.get("protocol_version", "")),
            packet_id=str(value.get("packet_id", "")),
            correlation_id=str(value.get("correlation_id", "")),
            source_node=str(value.get("source_node", "")),
            destination_node=str(value.get("destination_node", "")),
            event=MUEFEvent.from_dict(dict(value.get("event") or {})),
            qos=QoSProfile(**dict(value.get("qos") or {})),
        )
        packet.validate()
        return packet

    def validate(self) -> None:
        if self.protocol_version != CAMBUS_PROTOCOL_VERSION:
            raise ValueError("Unsupported CAMbus protocol version")
        if not self.packet_id or not self.correlation_id:
            raise ValueError("CAMbus packet and correlation IDs are required")
        if not self.source_node or not self.destination_node:
            raise ValueError("CAMbus source and destination nodes are required")
        self.event.validate()
        self.qos.validate()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if self.qos.max_latency_ms is None:
            value["qos"].pop("max_latency_ms")
        return value


def encode_packet(packet: SymbolPacket) -> bytes:
    packet.validate()
    payload = canonical_json_bytes(packet.to_dict())
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError("CAMbus frame exceeds maximum size")
    return payload


def decode_packet(payload: bytes) -> SymbolPacket:
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError("CAMbus frame exceeds maximum size")
    return SymbolPacket.from_dict(json.loads(payload.decode("utf-8")))


def send_frame(sock: socket.socket, packet: SymbolPacket) -> None:
    payload = encode_packet(packet)
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def receive_frame(sock: socket.socket) -> SymbolPacket:
    header = _recv_exact(sock, 4)
    length = struct.unpack("!I", header)[0]
    if length > MAX_FRAME_BYTES:
        raise ValueError("CAMbus frame exceeds maximum size")
    return decode_packet(_recv_exact(sock, length))


def send_tcp(address: tuple[str, int], packet: SymbolPacket, timeout: float = 5.0) -> None:
    with socket.create_connection(address, timeout=timeout) as sock:
        send_frame(sock, packet)


def receive_one_tcp(listener: socket.socket, timeout: float = 5.0) -> SymbolPacket:
    listener.settimeout(timeout)
    conn, _ = listener.accept()
    with conn:
        conn.settimeout(timeout)
        return receive_frame(conn)


def _recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("CAMbus connection closed before frame completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
