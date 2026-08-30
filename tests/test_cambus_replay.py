from __future__ import annotations

import socket
import tempfile
import threading
import unittest
from pathlib import Path

from migi.cambus import SymbolPacket, receive_one_tcp, send_tcp
from migi.events import MUEFEvent
from migi.genesis import GenesisNode


class CambusReplayTests(unittest.TestCase):
    def test_authorized_state_patch_replays_deterministically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            node = GenesisNode(root / "genesis.db", allowed_roots=[root])

            first = MUEFEvent.create(
                "migi.state.patch",
                actor_id="tester",
                payload={"state_patch": {"mode": "idle", "count": 1}},
            )
            second = MUEFEvent.create(
                "migi.state.patch",
                actor_id="tester",
                payload={"state_patch": {"mode": "active", "count": 2}},
            )

            r1 = node.process_muef_event(first)
            r2 = node.process_muef_event(second)

            self.assertEqual(r1["authority"]["tre_logic"], "+1")
            self.assertEqual(r2["authority"]["tre_logic"], "+1")
            self.assertEqual(r2["replay"]["state"], {"count": 2, "mode": "active"})
            self.assertEqual(r2["replay"]["applied_events"], 2)
            self.assertTrue(r2["replay"]["state_hash"])
            self.assertTrue(node.store.verify_chain()["valid"])

    def test_hold_event_is_preserved_but_not_applied(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            node = GenesisNode(root / "genesis.db", allowed_roots=[root])
            event = MUEFEvent.create(
                "migi.state.patch",
                actor_id="tester",
                payload={"state_patch": {"mode": "blocked"}},
            )

            result = node.process_muef_event(event, consent_scope="unspecified")

            self.assertEqual(result["authority"]["tre_logic"], "0")
            self.assertIsNone(result["execution"])
            self.assertEqual(result["replay"]["state"], {})
            self.assertEqual(result["replay"]["applied_events"], 0)
            self.assertEqual(result["replay"]["skipped_events"], 1)

    def test_two_nodes_send_muef_over_cambus_then_replay(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            node_b = GenesisNode(root / "node-b.db", allowed_roots=[root])

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            address = listener.getsockname()
            result_box: dict[str, object] = {}

            def receive_and_process() -> None:
                packet = receive_one_tcp(listener)
                result_box["result"] = node_b.process_muef_event(
                    packet.event,
                    transport_ref=packet.packet_id,
                )

            receiver = threading.Thread(target=receive_and_process)
            receiver.start()

            event = MUEFEvent.create(
                "migi.state.patch",
                actor_id="node-a",
                actor_type="service",
                payload={"state_patch": {"network_mode": "online"}},
            )
            packet = SymbolPacket.create(
                source_node="node-a",
                destination_node="node-b",
                event=event,
            )
            send_tcp((address[0], address[1]), packet)
            receiver.join(timeout=5)
            listener.close()

            self.assertFalse(receiver.is_alive())
            result = result_box["result"]
            self.assertEqual(result["authority"]["tre_logic"], "+1")
            self.assertEqual(result["replay"]["state"]["network_mode"], "online")
            self.assertEqual(result["receipt"]["metadata"]["transport_ref"], packet.packet_id)
            self.assertTrue(node_b.store.verify_chain()["valid"])


if __name__ == "__main__":
    unittest.main()
