"""Emoji A++ trit IR and deterministic MCP-boundary prototype.

This module intentionally uses a mock tool adapter. It does not connect to an
MCP server or claim production MCP protocol compatibility.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


SCHEMA_VERSION = "emoji-a-plus-plus.intent.v0"


class Trit(int, Enum):
    ABSORB = -1
    OBSERVE = 0
    EMIT = 1


SYMBOL_TO_TRIT = {"🌀": Trit.ABSORB, "⚛️": Trit.OBSERVE, "💠": Trit.EMIT}
TRIT_TO_SYMBOL = {value: key for key, value in SYMBOL_TO_TRIT.items()}


class AdapterError(ValueError):
    """Base error for invalid intents, tool requests, or adapter results."""


class PolicyDenied(AdapterError):
    """Raised when authority denies or holds a tool invocation."""


class TritSymbol(str, Enum):
    ABSORB = "🌀"
    OBSERVE = "⚛️"
    EMIT = "💠"


@dataclass(frozen=True)
class EmojiIntent:
    symbol: str
    operation: str
    target: str
    context: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    intent_id: str = ""

    @property
    def trit(self) -> Trit:
        try:
            return SYMBOL_TO_TRIT[self.symbol]
        except KeyError as exc:
            raise AdapterError(f"unsupported core trit symbol: {self.symbol!r}") from exc

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise AdapterError(f"unsupported schema version: {self.schema_version}")
        _ = self.trit
        if not self.operation.strip():
            raise AdapterError("operation is required")
        if not self.target.strip():
            raise AdapterError("target is required")
        if not isinstance(self.context, Mapping):
            raise AdapterError("context must be an object")
        # 🌐 is context metadata only; it is never accepted as a core trit.
        if self.context.get("network") is not None and not isinstance(self.context["network"], bool):
            raise AdapterError("context.network must be a boolean metadata flag")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "intent_id": self.intent_id,
            "symbol": self.symbol,
            "trit": int(self.trit),
            "operation": self.operation,
            "target": self.target,
            "context": dict(self.context),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EmojiIntent":
        if not isinstance(payload, Mapping):
            raise AdapterError("intent must be an object")
        allowed = {"schema_version", "intent_id", "symbol", "operation", "target", "context"}
        extra = set(payload) - allowed
        if extra:
            raise AdapterError(f"unknown intent fields: {sorted(extra)}")
        try:
            intent = cls(
                schema_version=payload.get("schema_version", SCHEMA_VERSION),
                intent_id=str(payload.get("intent_id", "")),
                symbol=payload["symbol"],
                operation=payload["operation"],
                target=payload["target"],
                context=payload.get("context", {}),
            )
        except KeyError as exc:
            raise AdapterError(f"missing required intent field: {exc.args[0]}") from exc
        intent.validate()
        return intent


@dataclass(frozen=True)
class MCPToolSpec:
    """Minimal mock tool definition using a deliberately small JSON Schema subset."""
    name: str
    input_schema: Mapping[str, Any]
    handler: Callable[[Mapping[str, Any]], Any] = field(compare=False, repr=False)


@dataclass(frozen=True)
class AuthorityDecision:
    state: str  # "allow", "hold", or "deny"
    reason: str


class AuthorityGate:
    """Explicit test gate. Production integration must use MIGI L2 authority."""
    def __init__(self, allowed_tools: set[str] | frozenset[str] = frozenset()):
        self.allowed_tools = frozenset(allowed_tools)

    def authorize(self, intent: EmojiIntent, tool: MCPToolSpec, arguments: Mapping[str, Any]) -> AuthorityDecision:
        if tool.name not in self.allowed_tools:
            return AuthorityDecision("deny", "policy.tool_not_allowlisted")
        if intent.trit is not Trit.EMIT:
            return AuthorityDecision("deny", "policy.emit_trit_required")
        if intent.operation != tool.name:
            return AuthorityDecision("deny", "policy.operation_tool_mismatch")
        return AuthorityDecision("allow", "test_gate.explicit_allowlist")


class MockMCPAdapter:
    """Deterministic in-process adapter; never connects to a network MCP server."""
    def __init__(self, tools: list[MCPToolSpec], authority: AuthorityGate):
        self.tools = {tool.name: tool for tool in tools}
        if len(self.tools) != len(tools):
            raise AdapterError("duplicate mock MCP tool names")
        self.authority = authority
        self.invocation_count = 0

    def invoke(self, intent: EmojiIntent, tool_name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        intent.validate()
        if intent.trit is not Trit.EMIT:
            raise PolicyDenied("tool invocation requires 💠 emit intent")
        if tool_name not in self.tools:
            raise AdapterError(f"unknown mock MCP tool: {tool_name}")
        if not isinstance(arguments, Mapping):
            raise AdapterError("tool arguments must be an object")

        tool = self.tools[tool_name]
        validate_tool_arguments(tool.input_schema, arguments)

        # Authority is checked after parsing/schema validation but before handler execution.
        decision = self.authority.authorize(intent, tool, arguments)
        if decision.state != "allow":
            raise PolicyDenied(f"{decision.state}: {decision.reason}")

        self.invocation_count += 1
        result = tool.handler(dict(arguments))
        canonical_result = _canonical_json(result)
        receipt_payload = {
            "schema_version": "migi.mock-mcp-receipt.v0",
            "intent": intent.to_dict(),
            "tool": tool.name,
            "arguments_sha256": hashlib.sha256(_canonical_json(dict(arguments)).encode("utf-8")).hexdigest(),
            "authority": {"state": decision.state, "reason": decision.reason},
            "result_sha256": hashlib.sha256(canonical_result.encode("utf-8")).hexdigest(),
            "result_class": "mock_tool_result",
        }
        receipt_payload["receipt_sha256"] = hashlib.sha256(_canonical_json(receipt_payload).encode("utf-8")).hexdigest()
        return {"result": result, "receipt": receipt_payload}


def validate_tool_arguments(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> None:
    """Validate a safe, small subset of JSON Schema for the offline prototype."""
    if schema.get("type") != "object":
        raise AdapterError("mock tool schema must have type=object")
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        raise AdapterError("invalid mock tool schema")
    missing = [key for key in required if key not in arguments]
    if missing:
        raise AdapterError(f"missing required tool arguments: {sorted(missing)}")
    if schema.get("additionalProperties", False) is False:
        extra = set(arguments) - set(properties)
        if extra:
            raise AdapterError(f"unknown tool arguments: {sorted(extra)}")

    for key, value in arguments.items():
        definition = properties.get(key)
        if definition is None:
            continue
        expected = definition.get("type")
        matches = {
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "object": lambda v: isinstance(v, Mapping),
            "array": lambda v: isinstance(v, list),
            "null": lambda v: v is None,
        }.get(expected)
        if matches is None:
            raise AdapterError(f"unsupported schema type for {key}: {expected}")
        if not matches(value):
            raise AdapterError(f"invalid type for tool argument {key}: expected {expected}")


def encode_intent(intent: EmojiIntent) -> str:
    """Canonical JSON encoding for deterministic tests; not a Morse wire format."""
    return _canonical_json(intent.to_dict())


def decode_intent(encoded: str) -> EmojiIntent:
    try:
        payload = json.loads(encoded)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AdapterError("encoded intent is not valid JSON") from exc
    return EmojiIntent.from_dict(payload)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise AdapterError("value is not canonical-JSON serializable") from exc
