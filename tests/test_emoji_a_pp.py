from __future__ import annotations

import unittest

from migi.emoji_a_pp import (
    AdapterError,
    AuthorityGate,
    EmojiIntent,
    MCPToolSpec,
    MockMCPAdapter,
    PolicyDenied,
    Trit,
    decode_intent,
    encode_intent,
)


class EmojiAPlusPlusTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        tool = MCPToolSpec(
            name="artifact.inspect",
            input_schema={
                "type": "object",
                "properties": {"artifact_id": {"type": "string"}},
                "required": ["artifact_id"],
                "additionalProperties": False,
            },
            handler=lambda args: self.calls.append(dict(args)) or {"inspected": args["artifact_id"]},
        )
        self.tool = tool

    def test_core_symbols_map_to_exactly_three_trits(self):
        self.assertEqual(EmojiIntent("🌀", "receive", "input").trit, Trit.ABSORB)
        self.assertEqual(EmojiIntent("⚛️", "inspect", "artifact").trit, Trit.OBSERVE)
        self.assertEqual(EmojiIntent("💠", "artifact.inspect", "artifact").trit, Trit.EMIT)

    def test_network_flag_is_separate_metadata_and_round_trips(self):
        intent = EmojiIntent("⚛️", "inspect", "artifact", context={"network": True, "region": "local"})
        decoded = decode_intent(encode_intent(intent))
        self.assertEqual(decoded.trit, Trit.OBSERVE)
        self.assertEqual(decoded.context["network"], True)
        self.assertNotIn("🌐", str(decoded.trit))

    def test_network_symbol_cannot_be_a_core_trit(self):
        intent = EmojiIntent("🌐", "artifact.inspect", "artifact")
        with self.assertRaises(AdapterError):
            intent.validate()

    def test_unknown_schema_version_fails_closed(self):
        intent = EmojiIntent("💠", "artifact.inspect", "artifact", schema_version="emoji-a-plus-plus.intent.v999")
        with self.assertRaises(AdapterError):
            intent.validate()

    def test_denied_authority_does_not_call_tool(self):
        adapter = MockMCPAdapter([self.tool], AuthorityGate(allowed_tools=set()))
        intent = EmojiIntent("💠", "artifact.inspect", "artifact")
        with self.assertRaises(PolicyDenied):
            adapter.invoke(intent, "artifact.inspect", {"artifact_id": "sample"})
        self.assertEqual(adapter.invocation_count, 0)
        self.assertEqual(self.calls, [])

    def test_non_emit_intent_does_not_call_tool(self):
        adapter = MockMCPAdapter([self.tool], AuthorityGate({"artifact.inspect"}))
        intent = EmojiIntent("⚛️", "artifact.inspect", "artifact")
        with self.assertRaises(PolicyDenied):
            adapter.invoke(intent, "artifact.inspect", {"artifact_id": "sample"})
        self.assertEqual(self.calls, [])

    def test_invalid_arguments_do_not_call_tool(self):
        adapter = MockMCPAdapter([self.tool], AuthorityGate({"artifact.inspect"}))
        intent = EmojiIntent("💠", "artifact.inspect", "artifact")
        with self.assertRaises(AdapterError):
            adapter.invoke(intent, "artifact.inspect", {"artifact_id": 42})
        self.assertEqual(self.calls, [])

    def test_authorized_mock_call_returns_provenance_receipt(self):
        adapter = MockMCPAdapter([self.tool], AuthorityGate({"artifact.inspect"}))
        intent = EmojiIntent("💠", "artifact.inspect", "artifact", intent_id="test-intent-1")
        result = adapter.invoke(intent, "artifact.inspect", {"artifact_id": "sample"})
        self.assertEqual(result["result"], {"inspected": "sample"})
        self.assertEqual(result["receipt"]["authority"]["state"], "allow")
        self.assertEqual(result["receipt"]["intent"]["intent_id"], "test-intent-1")
        self.assertEqual(len(result["receipt"]["receipt_sha256"]), 64)
        self.assertEqual(adapter.invocation_count, 1)
        self.assertEqual(len(self.calls), 1)

    def test_operation_tool_mismatch_is_denied(self):
        adapter = MockMCPAdapter([self.tool], AuthorityGate({"artifact.inspect"}))
        intent = EmojiIntent("💠", "different.operation", "artifact")
        with self.assertRaises(PolicyDenied):
            adapter.invoke(intent, "artifact.inspect", {"artifact_id": "sample"})
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
